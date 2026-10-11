/*
 * A2 scenario: 3GPP XR traffic (TR 26.926 cl. 6.5.3 / TR 38.838) over 802.11 with EDCA.
 *
 *   STA_i  <---- DL XR video (Tos 0xb8 -> UP 5 -> AC_VI) ----  AP
 *          ----- UL pose     (Tos 0xc0 -> UP 6 -> AC_VO) ---->   (optional)
 *
 * DL frame size  : truncated normal, mean M = R*1e6 / (E*F) / 8 [B]
 *                  (E = eye buffers per frame, E = 2 gives Table 6.5.3.1-1)
 *                  STD = sizeStdPct % of M, truncated to M +- sizeBoundPct % of M
 * DL frame times : periodic at E*F (eye buffers staggered), plus truncated
 *                  normal jitter (mean 0, STD jitterStd, |J| <= jitterMax) [ms]
 * UL pose        : 60 B payload every 10 ms (TR 26.926 cl. 5.9.2, 100 B incl. 40 B IP/UDP/RTP)
 *
 * Outputs (in --outDir):
 *   config.txt, tx_frames.csv, tx_packets.csv, rx_packets.csv, flowmon.xml, xr-wifi-*.pcap
 *
 * Run (from the ns-3 root, with this folder linked to scratch/xr-wifi):
 *   ./ns3 run "xr-wifi --rateMbps=10 --fps=60 --simTime=20 --outDir=a2-results"
 */

#include "xr-header.h"
#include "xr-traffic-app.h"

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/wifi-module.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("XrWifiScenario");

// ---------------------------------------------------------------- trace sinks

static void
FrameTxSink(std::ofstream* os,
            std::string flow,
            uint32_t frameId,
            uint32_t size,
            Time nominal)
{
    *os << flow << ',' << frameId << ',' << std::fixed << std::setprecision(9)
        << Simulator::Now().GetSeconds() << ',' << nominal.GetSeconds() << ',' << size << '\n';
}

static void
PacketTxSink(std::ofstream* os, std::string flow, uint32_t frameId, uint16_t fragIdx, uint32_t size)
{
    *os << flow << ',' << frameId << ',' << fragIdx << ',' << std::fixed << std::setprecision(9)
        << Simulator::Now().GetSeconds() << ',' << size << '\n';
}

static void
RxSink(std::ofstream* os, std::string flow, Ptr<const Packet> p)
{
    XrHeader hdr;
    if (p->GetSize() < XrHeader::SIZE || p->PeekHeader(hdr) != XrHeader::SIZE)
    {
        return;
    }
    const Time now = Simulator::Now();
    *os << flow << ',' << hdr.GetFrameId() << ',' << hdr.GetFragIdx() << ',' << std::fixed
        << std::setprecision(9) << now.GetSeconds() << ','
        << (now - hdr.GetTxTime()).GetSeconds() * 1e3 << ',' << p->GetSize() << '\n';
}

// ---------------------------------------------------------------- helpers

struct PhyProfile
{
    WifiStandard standard;
    std::string dataMode;
    std::string controlMode;
};

static PhyProfile
GetPhyProfile(const std::string& name)
{
    // all profiles use 20 MHz channels in the 5 GHz band
    static const std::map<std::string, PhyProfile> profiles{
        {"11a", {WIFI_STANDARD_80211a, "OfdmRate54Mbps", "OfdmRate24Mbps"}},
        {"11n", {WIFI_STANDARD_80211n, "HtMcs7", "OfdmRate24Mbps"}},
        {"11ac", {WIFI_STANDARD_80211ac, "VhtMcs8", "OfdmRate24Mbps"}},
        {"11ax", {WIFI_STANDARD_80211ax, "HeMcs11", "OfdmRate24Mbps"}},
    };
    auto it = profiles.find(name);
    NS_ABORT_MSG_IF(it == profiles.end(), "Unknown --standard " << name << " (11a|11n|11ac|11ax)");
    return it->second;
}

static Ptr<XrTrafficApp>
InstallXrApp(Ptr<Node> src,
             Address remote,
             uint8_t tos,
             double frameRate,
             Ptr<RandomVariableStream> size,
             Ptr<RandomVariableStream> jitter,
             uint32_t maxPayload,
             Time start,
             Time stop)
{
    auto app = CreateObject<XrTrafficApp>();
    app->SetAttribute("Remote", AddressValue(remote));
    app->SetAttribute("Tos", UintegerValue(tos));
    app->SetAttribute("FrameRate", DoubleValue(frameRate));
    app->SetAttribute("FrameSize", PointerValue(size));
    app->SetAttribute("Jitter", PointerValue(jitter));
    app->SetAttribute("MaxPayloadSize", UintegerValue(maxPayload));
    app->SetStartTime(start);
    app->SetStopTime(stop);
    src->AddApplication(app);
    return app;
}

static Ptr<NormalRandomVariable>
TruncatedNormal(double mean, double stddev, double bound)
{
    // ns-3 NormalRandomVariable rejects samples with |x - mean| > Bound,
    // which is exactly a symmetric truncated normal distribution
    auto rv = CreateObject<NormalRandomVariable>();
    rv->SetAttribute("Mean", DoubleValue(mean));
    rv->SetAttribute("Variance", DoubleValue(stddev * stddev));
    rv->SetAttribute("Bound", DoubleValue(bound));
    return rv;
}

// ---------------------------------------------------------------- main

int
main(int argc, char* argv[])
{
    // scenario
    std::string standard{"11a"};
    std::string dataMode{""};
    double distance{5.0};
    uint32_t nSta{1};
    double simTime{20.0};
    double appStart{1.0};
    uint32_t run{1};
    std::string outDir{"a2-results"};
    bool pcap{true};
    // DL XR video model
    double rateMbps{10.0};
    double fps{60.0};
    uint32_t eyeBuffers{2};
    double sizeStdPct{10.5};
    double sizeBoundPct{50.0};
    double jitterStd{2.0};
    double jitterMax{4.0};
    uint32_t maxPayload{1472};
    // UL pose model
    bool enableUplink{false};
    double poseRateHz{100.0};
    uint32_t poseSize{60};

    CommandLine cmd(__FILE__);
    cmd.AddValue("standard", "Wi-Fi standard: 11a, 11n, 11ac, 11ax", standard);
    cmd.AddValue("dataMode", "Constant data mode (empty = profile default)", dataMode);
    cmd.AddValue("distance", "AP to STA distance [m]", distance);
    cmd.AddValue("nSta", "Number of stations", nSta);
    cmd.AddValue("simTime", "Application stop time [s]", simTime);
    cmd.AddValue("appStart", "Application start time [s]", appStart);
    cmd.AddValue("run", "RNG run number", run);
    cmd.AddValue("outDir", "Output directory", outDir);
    cmd.AddValue("pcap", "Write PCAP files of AP and STA 0", pcap);
    cmd.AddValue("rateMbps", "DL XR data rate R [Mbit/s]", rateMbps);
    cmd.AddValue("fps", "Frame rate F [fps]", fps);
    cmd.AddValue("eyeBuffers", "Eye buffers per frame E (2 = TR 26.926 Table 6.5.3.1-1)", eyeBuffers);
    cmd.AddValue("sizeStdPct", "Frame size STD in % of mean", sizeStdPct);
    cmd.AddValue("sizeBoundPct", "Frame size truncation in % of mean (symmetric)", sizeBoundPct);
    cmd.AddValue("jitterStd", "Jitter STD [ms]", jitterStd);
    cmd.AddValue("jitterMax", "Jitter truncation |J| <= jitterMax [ms]", jitterMax);
    cmd.AddValue("maxPayload", "Max UDP payload per packet [B]", maxPayload);
    cmd.AddValue("enableUplink", "Enable UL pose traffic", enableUplink);
    cmd.AddValue("poseRateHz", "UL pose rate [Hz]", poseRateHz);
    cmd.AddValue("poseSize", "UL pose payload [B]", poseSize);
    cmd.Parse(argc, argv);

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(run);
    std::filesystem::create_directories(outDir);

    const double bufferRate = fps * eyeBuffers;            // generated units per second
    const double meanSize = rateMbps * 1e6 / bufferRate / 8; // M [B]
    const PhyProfile prof = GetPhyProfile(standard);
    if (dataMode.empty())
    {
        dataMode = prof.dataMode;
    }

    std::cout << "=== XR over Wi-Fi (A2) ===\n"
              << "standard " << standard << ", data mode " << dataMode << ", nSta " << nSta
              << ", distance " << distance << " m, run " << run << "\n"
              << "DL video: R " << rateMbps << " Mbit/s, F " << fps << " fps x " << eyeBuffers
              << " eye buffers -> " << bufferRate << " Hz, M " << meanSize << " B, STD "
              << sizeStdPct << " %, bound +-" << sizeBoundPct << " %, jitter STD " << jitterStd
              << " ms, |J| <= " << jitterMax << " ms\n"
              << "UL pose: " << (enableUplink ? "on" : "off") << "\n";

    // model parameters for the verification script (key=value)
    {
        std::ofstream cfg(outDir + "/config.txt");
        cfg << "standard=" << standard << "\ndataMode=" << dataMode << "\nnSta=" << nSta
            << "\ndistance=" << distance << "\nrun=" << run << "\nsimTime=" << simTime
            << "\nrateMbps=" << rateMbps << "\nfps=" << fps << "\neyeBuffers=" << eyeBuffers
            << "\nmeanSize=" << meanSize << "\nsizeStdPct=" << sizeStdPct
            << "\nsizeBoundPct=" << sizeBoundPct << "\njitterStd=" << jitterStd
            << "\njitterMax=" << jitterMax << "\nmaxPayload=" << maxPayload
            << "\nenableUplink=" << enableUplink << "\nposeRateHz=" << poseRateHz
            << "\nposeSize=" << poseSize << "\n";
    }

    // ------------------------------------------------------------ nodes, mobility
    NodeContainer apNode(1);
    NodeContainer staNodes(nSta);

    MobilityHelper mobility;
    auto pos = CreateObject<ListPositionAllocator>();
    pos->Add(Vector(0.0, 0.0, 0.0));
    for (uint32_t i = 0; i < nSta; ++i)
    {
        const double phi = 2 * M_PI * i / nSta;
        pos->Add(Vector(distance * std::cos(phi), distance * std::sin(phi), 0.0));
    }
    mobility.SetPositionAllocator(pos);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(apNode);
    mobility.Install(staNodes);

    // ------------------------------------------------------------ Wi-Fi
    YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());
    phy.Set("ChannelSettings", StringValue("{36, 20, BAND_5GHZ, 0}"));
    phy.SetPcapDataLinkType(WifiPhyHelper::DLT_IEEE802_11_RADIO);

    WifiHelper wifi;
    wifi.SetStandard(prof.standard);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode",
                                 StringValue(dataMode),
                                 "ControlMode",
                                 StringValue(prof.controlMode));

    WifiMacHelper mac;
    Ssid ssid("mwn-a2");
    mac.SetType("ns3::StaWifiMac", "QosSupported", BooleanValue(true), "Ssid", SsidValue(ssid));
    NetDeviceContainer staDevs = wifi.Install(phy, mac, staNodes);
    mac.SetType("ns3::ApWifiMac", "QosSupported", BooleanValue(true), "Ssid", SsidValue(ssid));
    NetDeviceContainer apDev = wifi.Install(phy, mac, apNode);

    // ------------------------------------------------------------ IP
    InternetStackHelper stack;
    stack.Install(apNode);
    stack.Install(staNodes);
    Ipv4AddressHelper addr("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer apIf = addr.Assign(apDev);
    Ipv4InterfaceContainer staIf = addr.Assign(staDevs);

    // ------------------------------------------------------------ trace files
    std::ofstream txFrames(outDir + "/tx_frames.csv");
    std::ofstream txPackets(outDir + "/tx_packets.csv");
    std::ofstream rxPackets(outDir + "/rx_packets.csv");
    txFrames << "flow,frame_id,time_s,nominal_s,size_B\n";
    txPackets << "flow,frame_id,frag_idx,time_s,size_B\n";
    rxPackets << "flow,frame_id,frag_idx,time_s,delay_ms,size_B\n";

    // ------------------------------------------------------------ applications
    const Time start = Seconds(appStart);
    const Time stop = Seconds(simTime);
    int64_t stream = 1000;

    for (uint32_t i = 0; i < nSta; ++i)
    {
        // DL XR video, AP -> STA i
        const std::string dlName = "dl_sta" + std::to_string(i);
        const uint16_t dlPort = 5000 + i;
        PacketSinkHelper dlSinkHelper("ns3::UdpSocketFactory",
                                      InetSocketAddress(Ipv4Address::GetAny(), dlPort));
        ApplicationContainer dlSink = dlSinkHelper.Install(staNodes.Get(i));
        dlSink.Start(Seconds(0.0));
        dlSink.Get(0)->TraceConnectWithoutContext(
            "RxWithoutAddress",
            MakeBoundCallback(&RxSink, &rxPackets, dlName));

        auto dl = InstallXrApp(
            apNode.Get(0),
            InetSocketAddress(staIf.GetAddress(i), dlPort),
            0xb8, // UP 5 -> AC_VI
            bufferRate,
            TruncatedNormal(meanSize, meanSize * sizeStdPct / 100, meanSize * sizeBoundPct / 100),
            TruncatedNormal(0.0, jitterStd, jitterMax),
            maxPayload,
            start + MilliSeconds(i), // small offset so STAs are not frame aligned
            stop);
        stream += dl->AssignStreams(stream);
        dl->TraceConnectWithoutContext("FrameTx",
                                       MakeBoundCallback(&FrameTxSink, &txFrames, dlName));
        dl->TraceConnectWithoutContext("PacketTx",
                                       MakeBoundCallback(&PacketTxSink, &txPackets, dlName));

        if (!enableUplink)
        {
            continue;
        }

        // UL pose, STA i -> AP
        const std::string ulName = "ul_sta" + std::to_string(i);
        const uint16_t ulPort = 6000 + i;
        PacketSinkHelper ulSinkHelper("ns3::UdpSocketFactory",
                                      InetSocketAddress(Ipv4Address::GetAny(), ulPort));
        ApplicationContainer ulSink = ulSinkHelper.Install(apNode.Get(0));
        ulSink.Start(Seconds(0.0));
        ulSink.Get(0)->TraceConnectWithoutContext(
            "RxWithoutAddress",
            MakeBoundCallback(&RxSink, &rxPackets, ulName));

        auto poseSizeRv = CreateObject<ConstantRandomVariable>();
        poseSizeRv->SetAttribute("Constant", DoubleValue(poseSize));
        auto noJitter = CreateObject<ConstantRandomVariable>();
        noJitter->SetAttribute("Constant", DoubleValue(0.0));

        auto ul = InstallXrApp(staNodes.Get(i),
                               InetSocketAddress(apIf.GetAddress(0), ulPort),
                               0xc0, // UP 6 -> AC_VO
                               poseRateHz,
                               poseSizeRv,
                               noJitter,
                               maxPayload,
                               start + MilliSeconds(i),
                               stop);
        stream += ul->AssignStreams(stream);
        ul->TraceConnectWithoutContext("FrameTx",
                                       MakeBoundCallback(&FrameTxSink, &txFrames, ulName));
        ul->TraceConnectWithoutContext("PacketTx",
                                       MakeBoundCallback(&PacketTxSink, &txPackets, ulName));
    }

    // ------------------------------------------------------------ PCAP, FlowMonitor
    if (pcap)
    {
        phy.EnablePcap(outDir + "/xr-wifi-ap", apDev.Get(0));
        phy.EnablePcap(outDir + "/xr-wifi-sta", staDevs.Get(0));
    }

    FlowMonitorHelper fmHelper;
    Ptr<FlowMonitor> monitor = fmHelper.InstallAll();

    Simulator::Stop(stop + Seconds(0.5)); // let in-flight packets drain
    Simulator::Run();

    // ------------------------------------------------------------ results
    monitor->CheckForLostPackets();
    auto classifier = DynamicCast<Ipv4FlowClassifier>(fmHelper.GetClassifier());
    std::cout << "\n=== FlowMonitor results ===\n";
    for (const auto& [id, st] : monitor->GetFlowStats())
    {
        const auto t = classifier->FindFlow(id);
        const double dur = (st.timeLastRxPacket - st.timeFirstTxPacket).GetSeconds();
        const double thr = dur > 0 ? st.rxBytes * 8.0 / dur / 1e6 : 0.0;
        const double loss = st.txPackets ? 100.0 * (st.txPackets - st.rxPackets) / st.txPackets : 0.0;
        std::cout << "Flow " << id << " " << t.sourceAddress << ":" << t.sourcePort << " -> "
                  << t.destinationAddress << ":" << t.destinationPort << "\n"
                  << "  tx/rx packets : " << st.txPackets << " / " << st.rxPackets << " (loss "
                  << std::setprecision(3) << loss << " %)\n"
                  << "  throughput    : " << thr << " Mbit/s\n";
        if (st.rxPackets > 0)
        {
            std::cout << "  mean delay    : " << st.delaySum.GetSeconds() / st.rxPackets * 1e3
                      << " ms\n";
        }
        if (st.rxPackets > 1)
        {
            std::cout << "  mean jitter   : "
                      << st.jitterSum.GetSeconds() / (st.rxPackets - 1) * 1e3 << " ms\n";
        }
    }
    monitor->SerializeToXmlFile(outDir + "/flowmon.xml", true, true);

    Simulator::Destroy();
    txFrames.close();
    txPackets.close();
    rxPackets.close();
    std::cout << "\nTraces written to " << outDir << "/\n";
    return 0;
}