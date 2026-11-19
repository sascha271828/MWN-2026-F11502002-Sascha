/*
 * A4 baseline: reproduction of Fig. 8 of
 *   S. Mangold, S. Choi, G. R. Hiertz, O. Klein, B. Walke,
 *   "Analysis of IEEE 802.11e for QoS Support in Wireless LANs",
 *   IEEE Wireless Communications, Dec. 2003.
 *
 * Scenario (one isolated QBSS, 802.11a, all frames at 24 Mb/s):
 *
 *            +--> STA 0   4 streams (AC_VO, AC_VI, AC_BE, AC_BK)
 *   AP (HC) -+--> STA 1   4 streams
 *            +--> STA 2   4 streams
 *
 *   The AP is the only data transmitter: 12 downlink streams, 3 per AC.
 *   Only virtual (internal) collisions between the four EDCA backoff
 *   entities of the AP occur. The stations only send ACKs.
 *
 * Traffic   : per stream, MSDUs of 512 byte with negative exponentially
 *             distributed inter-arrival times (XrTrafficApp in POISSON mode).
 *             "MSDU" is counted as the frame body handed to the MAC:
 *             LLC/SNAP 8 + IPv4 20 + UDP 8 + UDP payload = 512 byte.
 * x axis    : offered traffic per AC (sum of its 3 streams) [Mb/s], --load
 * y axis    : throughput per AC (sum of its 3 streams) [Mb/s], counted in
 *             delivered MSDU bytes inside the measurement window
 * EDCA      : Table 1 of the paper, TXOP limit 0 (one data frame per TXOP)
 *
 * The same program covers three experiments (see scripts/run.sh):
 *   fig8    --load=x                      all four ACs at the same load
 *   simple  --loadVO=30 --loadVI=0 ...    a subset of the ACs, saturated
 *   pilot   --viModel=burst               AC_VI sends periodic bursts
 *                                         (video frames) at the same mean load
 *
 * Final project option, off by default so that the A4 baseline is unchanged:
 *   --uplinkPose=true   every station sends an XR pose stream to the AP on
 *                       AC_VO (TR 26.926 cl. 5.9.2, as in A2: 60 byte payload
 *                       every 10 ms). The stations then contend with the AP,
 *                       so real collisions occur. The stream is reported as an
 *                       extra row "UL_POSE", and the column ack_timeouts
 *                       (data frames without ACK = collisions on the error
 *                       free channel) is added to every row.
 *
 * One program run is one (configuration, run number) point. It appends one
 * row per AC to --outFile and, if --delayFile is set, the delay histograms.
 *
 * Run (from the ns-3 root, with this folder linked to scratch/edca-fig8):
 *   ./ns3 run "edca-fig8 --load=6 --run=1 --outFile=fig8.csv"
 */

#include "xr-header.h"
#include "xr-traffic-app.h"

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/traffic-control-module.h"
#include "ns3/wifi-module.h"

#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("EdcaFig8");

// ---------------------------------------------------------------- access categories

/// Per AC configuration: EDCA parameter set of Table 1 of the paper and the
/// IP ToS value that ns-3 maps to this AC (TID = ToS >> 5).
struct AcConfig
{
    const char* name;
    AcIndex ac;
    uint8_t tos;
    uint8_t aifsn;
    uint32_t cwMin;
    uint32_t cwMax;
};

static const std::array<AcConfig, 4> g_acs{{
    {"AC_VO", AC_VO, 0xc0, 2, 3, 7},     // UP 6
    {"AC_VI", AC_VI, 0xb8, 2, 7, 15},    // UP 5
    {"AC_BE", AC_BE, 0x00, 3, 15, 1023}, // UP 0
    {"AC_BK", AC_BK, 0x20, 7, 15, 1023}, // UP 1
}};

/// Header overhead between UDP payload and MSDU: LLC/SNAP 8 + IPv4 20 + UDP 8
static const uint32_t g_overhead = 36;

/// Index into g_acs for an ns-3 AcIndex, or -1
static int
AcSlot(AcIndex ac)
{
    for (std::size_t i = 0; i < g_acs.size(); ++i)
    {
        if (g_acs[i].ac == ac)
        {
            return static_cast<int>(i);
        }
    }
    return -1;
}

// ---------------------------------------------------------------- statistics

/// Delay histogram with fixed bin width. Delays beyond the range are counted
/// in the last bin, which is reported separately (never silently dropped).
class DelayHistogram
{
  public:
    static constexpr double BIN_US = 50.0;
    static constexpr std::size_t N_BINS = 40000; // 2 s

    void Add(Time d)
    {
        const double us = d.GetSeconds() * 1e6;
        const auto bin = std::min<std::size_t>(static_cast<std::size_t>(us / BIN_US), N_BINS);
        ++m_bins[bin];
    }

    /// (upper bin edge [us], count) for all non empty bins
    void Write(std::ostream& os, const std::string& prefix) const
    {
        for (std::size_t i = 0; i <= N_BINS; ++i)
        {
            if (m_bins[i] > 0)
            {
                os << prefix << ',' << (i + 1) * BIN_US << ',' << m_bins[i] << '\n';
            }
        }
    }

  private:
    std::vector<uint64_t> m_bins = std::vector<uint64_t>(N_BINS + 1, 0);
};

/// Counters of one AC, only updated inside the measurement window
struct AcStats
{
    uint64_t txPkts{0};       //!< packets (MSDUs) generated by the sources
    uint64_t txBytes{0};      //!< MSDU bytes generated by the sources
    uint64_t rxPkts{0};       //!< packets delivered to the sinks
    uint64_t rxBytes{0};      //!< MSDU bytes delivered to the sinks
    double delaySum{0};       //!< sum of packet delays, source to sink [s]
    double delaySqSum{0};     //!< sum of squared packet delays [s^2]
    uint64_t txFrames{0};     //!< application frames generated (1 MSDU each for Poisson)
    uint64_t rxFrames{0};     //!< application frames received completely
    double frameDelaySum{0};  //!< sum of frame delays (last fragment received) [s]
    uint64_t dropQueue{0};    //!< MAC queue full (TcDrop or WIFI_MAC_DROP_FAILED_ENQUEUE)
    uint64_t dropLifetime{0}; //!< MSDU lifetime exceeded (WIFI_MAC_DROP_EXPIRED_LIFETIME)
    uint64_t dropRetry{0};    //!< retry limit reached (WIFI_MAC_DROP_REACHED_RETRY_LIMIT)
    DelayHistogram pktDelay;
    DelayHistogram frameDelay;
};

/// Row of the uplink pose stream (all stations) behind the four downlink ACs
static const int g_poseSlot = 4;
static std::array<AcStats, 5> g_stats;
/// Data frames whose ACK did not arrive, inside the window, same rows as g_stats
static std::array<uint64_t, 5> g_ackTimeouts{};

static const char*
RowName(int slot)
{
    return slot == g_poseSlot ? "UL_POSE" : g_acs[slot].name;
}
static Time g_measStart;
static Time g_measEnd;

/// Fragments received per frame, key: (AC slot, stream) -> frame id -> count
static std::map<std::pair<int, uint32_t>, std::map<uint32_t, uint16_t>> g_reassembly;

static bool
InWindow()
{
    const Time now = Simulator::Now();
    return now >= g_measStart && now < g_measEnd;
}

/// Optional log of every generated MSDU (for the traffic model verification)
static std::ofstream g_arrivalLog;

static void
PacketTxSink(int slot,
             uint32_t streamIdx,
             uint32_t frameId,
             uint16_t /* fragIdx */,
             uint32_t size)
{
    if (InWindow())
    {
        ++g_stats[slot].txPkts;
        g_stats[slot].txBytes += size + g_overhead;
        if (g_arrivalLog.is_open())
        {
            g_arrivalLog << RowName(slot) << ',' << streamIdx << ',' << frameId << ','
                         << Simulator::Now().GetNanoSeconds() << ',' << size + g_overhead << '\n';
        }
    }
}

static void
FrameTxSink(int slot, uint32_t /* frameId */, uint32_t /* size */, Time /* nominal */)
{
    if (InWindow())
    {
        ++g_stats[slot].txFrames;
    }
}

static void
RxSink(int slot, uint32_t streamIdx, Ptr<const Packet> p)
{
    if (!InWindow())
    {
        return;
    }
    XrHeader hdr;
    NS_ABORT_MSG_IF(p->GetSize() < XrHeader::SIZE || p->PeekHeader(hdr) != XrHeader::SIZE,
                    "Received a packet without XrHeader");
    const Time d = Simulator::Now() - hdr.GetTxTime();
    AcStats& s = g_stats[slot];
    ++s.rxPkts;
    s.rxBytes += p->GetSize() + g_overhead;
    s.delaySum += d.GetSeconds();
    s.delaySqSum += d.GetSeconds() * d.GetSeconds();
    s.pktDelay.Add(d);

    // frame level: complete when all fragments have arrived. Only frames that
    // were sent inside the window are counted (as in txFrames).
    if (hdr.GetTxTime() < g_measStart)
    {
        return;
    }
    bool complete = hdr.GetNFrags() == 1;
    if (!complete)
    {
        auto& frames = g_reassembly[{slot, streamIdx}];
        if (++frames[hdr.GetFrameId()] == hdr.GetNFrags())
        {
            frames.erase(hdr.GetFrameId());
            complete = true;
        }
    }
    if (complete)
    {
        ++s.rxFrames;
        s.frameDelaySum += d.GetSeconds();
        s.frameDelay.Add(d);
    }
}

static void
DroppedMpduSink(WifiMacDropReason reason, Ptr<const WifiMpdu> mpdu)
{
    if (!InWindow() || !mpdu->GetHeader().IsQosData())
    {
        return;
    }
    const int slot = AcSlot(QosUtilsMapTidToAc(mpdu->GetHeader().GetQosTid()));
    if (slot < 0)
    {
        return;
    }
    switch (reason)
    {
    case WIFI_MAC_DROP_FAILED_ENQUEUE:
        ++g_stats[slot].dropQueue;
        break;
    case WIFI_MAC_DROP_EXPIRED_LIFETIME:
        ++g_stats[slot].dropLifetime;
        break;
    case WIFI_MAC_DROP_REACHED_RETRY_LIMIT:
        ++g_stats[slot].dropRetry;
        break;
    default:
        break;
    }
}

/// Drops in the MAC of a station: everything it sends is the pose stream
static void
StaDroppedMpduSink(WifiMacDropReason reason, Ptr<const WifiMpdu> mpdu)
{
    if (!InWindow() || !mpdu->GetHeader().IsQosData())
    {
        return;
    }
    AcStats& s = g_stats[g_poseSlot];
    switch (reason)
    {
    case WIFI_MAC_DROP_FAILED_ENQUEUE:
        ++s.dropQueue;
        break;
    case WIFI_MAC_DROP_EXPIRED_LIFETIME:
        ++s.dropLifetime;
        break;
    case WIFI_MAC_DROP_REACHED_RETRY_LIMIT:
        ++s.dropRetry;
        break;
    default:
        break;
    }
}

static void
StaTcDropSink(Ptr<const Packet> /* p */)
{
    if (InWindow())
    {
        ++g_stats[g_poseSlot].dropQueue;
    }
}

/// Missing ACK after a data frame. fromAp: downlink frame, row = its AC,
/// otherwise a pose frame of a station.
static void
AckTimeoutSink(bool fromAp, uint8_t /* reason */, Ptr<const WifiMpdu> mpdu, const WifiTxVector&)
{
    if (!InWindow() || !mpdu->GetHeader().IsQosData())
    {
        return;
    }
    const int slot = fromAp ? AcSlot(QosUtilsMapTidToAc(mpdu->GetHeader().GetQosTid()))
                            : g_poseSlot;
    if (slot >= 0)
    {
        ++g_ackTimeouts[slot];
    }
}

/// Tail drop above the MAC. Without a queue disc the traffic control layer
/// hands a packet to the device only while the MAC queue of its AC has room
/// (flow control), otherwise it drops the packet and fires TcDrop. The packet
/// already carries its IPv4 header, the ToS identifies the AC.
static void
TcDropSink(Ptr<const Packet> p)
{
    Ipv4Header ip;
    if (!InWindow() || p->PeekHeader(ip) == 0)
    {
        return;
    }
    const int slot = AcSlot(QosUtilsMapTidToAc(ip.GetTos() >> 5));
    if (slot >= 0)
    {
        ++g_stats[slot].dropQueue;
    }
}

// ---------------------------------------------------------------- main

int
main(int argc, char* argv[])
{
    // sweep point
    double load{6.0}; // offered traffic per AC [Mb/s]
    uint32_t run{1};
    // per AC override of --load: negative = use --load, 0 = AC carries no traffic
    std::array<double, 4> acLoad{-1.0, -1.0, -1.0, -1.0};
    // traffic
    uint32_t nSta{3};       // streams per AC (one per station)
    uint32_t msduSize{512}; // [byte], incl. LLC/SNAP, IP and UDP headers
    // AC_VI arrival process (pilot for the final project)
    std::string viModel{"poisson"}; // poisson | burst
    double viFps{60.0};             // burst: video frames per second and stream
    std::string viPhase{"random"};  // burst: random | aligned frame phases of the streams
    // uplink pose stream of every station (final project), TR 26.926 cl. 5.9.2
    bool uplinkPose{false};
    double poseRateHz{100.0};  // one pose packet every 10 ms
    uint32_t posePayload{60};  // [byte] UDP payload, MSDU = payload + 36
    // timing
    double appStart{1.0};  // [s] association phase before the sources start
    double warmup{1.0};    // [s] excluded from the measurement
    double measTime{30.0}; // [s] measurement window
    // PHY / MAC
    std::string dataMode{"OfdmRate24Mbps"};
    double distance{5.0};
    bool defaultTxop{false};
    std::string queueSize{"500p"};
    double queueDelayMs{500.0};
    uint32_t retryLimit{7};
    bool qdisc{false};
    bool beacons{false};
    // output
    std::string tag{"fig8"};
    std::string outFile{"fig8.csv"};
    std::string delayFile;
    std::string arrivalFile;
    std::string pcapPrefix;
    bool verbose{true};

    CommandLine cmd(__FILE__);
    cmd.AddValue("load", "Offered traffic per AC, sum of its streams [Mb/s]", load);
    cmd.AddValue("loadVO", "Offered traffic of AC_VO [Mb/s] (negative: --load, 0: off)", acLoad[0]);
    cmd.AddValue("loadVI", "Offered traffic of AC_VI [Mb/s] (negative: --load, 0: off)", acLoad[1]);
    cmd.AddValue("loadBE", "Offered traffic of AC_BE [Mb/s] (negative: --load, 0: off)", acLoad[2]);
    cmd.AddValue("loadBK", "Offered traffic of AC_BK [Mb/s] (negative: --load, 0: off)", acLoad[3]);
    cmd.AddValue("run", "RNG run number (seed is fixed to 1)", run);
    cmd.AddValue("nSta", "Number of stations = streams per AC", nSta);
    cmd.AddValue("msduSize", "MSDU size incl. LLC/SNAP, IP, UDP headers [byte]", msduSize);
    cmd.AddValue("viModel",
                 "Arrival process of the AC_VI streams: poisson (as all other ACs) or "
                 "burst (periodic video frames, each a burst of MSDUs)",
                 viModel);
    cmd.AddValue("viFps", "burst: frame rate per AC_VI stream [1/s]", viFps);
    cmd.AddValue("viPhase",
                 "burst: random (independent frame phase per stream) or aligned "
                 "(all streams send their frames at the same instant)",
                 viPhase);
    cmd.AddValue("uplinkPose",
                 "Every station sends a pose stream to the AP on AC_VO (real contention)",
                 uplinkPose);
    cmd.AddValue("poseRateHz", "uplinkPose: pose packets per second and station", poseRateHz);
    cmd.AddValue("posePayload", "uplinkPose: UDP payload of a pose packet [byte]", posePayload);
    cmd.AddValue("appStart", "Start time of the sources [s]", appStart);
    cmd.AddValue("warmup", "Warm-up after the source start, not measured [s]", warmup);
    cmd.AddValue("measTime", "Measurement window [s]", measTime);
    cmd.AddValue("dataMode",
                 "Constant rate of the data frames. ns-3 derives the ACK rate from it "
                 "(24 Mb/s for 24 Mb/s data in 802.11a)",
                 dataMode);
    cmd.AddValue("distance", "AP to STA distance [m]", distance);
    cmd.AddValue("defaultTxop",
                 "Keep the ns-3 default TXOP limits (false: 0 = one frame per TXOP)",
                 defaultTxop);
    cmd.AddValue("queueSize", "WifiMacQueue MaxSize per AC", queueSize);
    cmd.AddValue("queueDelayMs", "WifiMacQueue MaxDelay (MSDU lifetime) [ms]", queueDelayMs);
    cmd.AddValue("retryLimit", "WifiMac FrameRetryLimit (failed attempts per MSDU)", retryLimit);
    cmd.AddValue("qdisc",
                 "Keep the default traffic control queue disc above the MAC "
                 "(its drops are not counted in drop_queue)",
                 qdisc);
    cmd.AddValue("beacons",
                 "Keep beacons during the measurement (false: as in the paper, the AP "
                 "stops sending beacons when the sources start)",
                 beacons);
    cmd.AddValue("tag", "Label of the configuration, copied to the CSV", tag);
    cmd.AddValue("outFile", "CSV file, rows are appended", outFile);
    cmd.AddValue("delayFile", "CSV file for the delay histograms (empty: not written)", delayFile);
    cmd.AddValue("arrivalFile",
                 "CSV file with the generation time of every MSDU (empty: not written)",
                 arrivalFile);
    cmd.AddValue("pcapPrefix",
                 "File prefix for a PCAP trace of the AP (empty: no trace), for Wireshark",
                 pcapPrefix);
    cmd.AddValue("verbose", "Print configuration and results", verbose);
    cmd.Parse(argc, argv);

    NS_ABORT_MSG_IF(msduSize < g_overhead + XrHeader::SIZE, "msduSize too small");
    NS_ABORT_MSG_IF(load <= 0, "load must be positive");
    NS_ABORT_MSG_IF(uplinkPose && (poseRateHz <= 0 || posePayload < XrHeader::SIZE),
                    "uplinkPose: poseRateHz must be positive, posePayload >= XrHeader");
    NS_ABORT_MSG_IF(viModel != "poisson" && viModel != "burst", "viModel: poisson or burst");
    NS_ABORT_MSG_IF(viPhase != "random" && viPhase != "aligned", "viPhase: random or aligned");
    NS_ABORT_MSG_IF(QueueSize(queueSize).GetUnit() != QueueSizeUnit::PACKETS,
                    "queueSize must be given in packets, e.g. 500p");
    const uint32_t payload = msduSize - g_overhead; // UDP payload of a full MSDU
    for (auto& l : acLoad)
    {
        if (l < 0)
        {
            l = load;
        }
    }

    RngSeedManager::SetSeed(1);
    RngSeedManager::SetRun(run);

    Config::SetDefault("ns3::WifiMacQueue::MaxSize", StringValue(queueSize));
    Config::SetDefault("ns3::WifiMacQueue::MaxDelay", TimeValue(MilliSeconds(queueDelayMs)));
    Config::SetDefault("ns3::WifiMac::FrameRetryLimit", UintegerValue(retryLimit));
    if (!beacons)
    {
        // the stations must not restart their association when the beacons stop
        Config::SetDefault("ns3::StaWifiMac::MaxMissedBeacons", UintegerValue(1000000));
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

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211a);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                 "DataMode",
                                 StringValue(dataMode),
                                 "ControlMode",
                                 StringValue(dataMode));

    WifiMacHelper mac;
    Ssid ssid("mwn-a4");
    mac.SetType("ns3::StaWifiMac", "QosSupported", BooleanValue(true), "Ssid", SsidValue(ssid));
    NetDeviceContainer staDevs = wifi.Install(phy, mac, staNodes);
    mac.SetType("ns3::ApWifiMac", "QosSupported", BooleanValue(true), "Ssid", SsidValue(ssid));
    NetDeviceContainer apDev = wifi.Install(phy, mac, apNode);

    if (!pcapPrefix.empty())
    {
        phy.SetPcapDataLinkType(WifiPhyHelper::DLT_IEEE802_11_RADIO);
        phy.EnablePcap(pcapPrefix, apDev.Get(0));
    }

    // fixed RNG streams for backoff etc., so that a (seed, run) pair is repeatable
    int64_t stream = 100;
    stream += WifiHelper::AssignStreams(apDev, stream);
    stream += WifiHelper::AssignStreams(staDevs, stream);

    // EDCA parameter set of Table 1 on the AP (the only data transmitter)
    Ptr<WifiMac> apMac = DynamicCast<WifiNetDevice>(apDev.Get(0))->GetMac();
    for (const auto& a : g_acs)
    {
        Ptr<QosTxop> txop = apMac->GetQosTxop(a.ac);
        txop->SetAifsn(a.aifsn);
        txop->SetMinCw(a.cwMin);
        txop->SetMaxCw(a.cwMax);
        if (!defaultTxop)
        {
            txop->SetTxopLimit(Time(0)); // one data frame per TXOP
        }
    }
    apMac->TraceConnectWithoutContext("DroppedMpdu", MakeCallback(&DroppedMpduSink));
    if (uplinkPose)
    {
        // The stations become transmitters: same EDCA parameter set as the AP
        apMac->TraceConnectWithoutContext("MpduResponseTimeout",
                                          MakeBoundCallback(&AckTimeoutSink, true));
        for (uint32_t i = 0; i < nSta; ++i)
        {
            Ptr<WifiMac> staMac = DynamicCast<WifiNetDevice>(staDevs.Get(i))->GetMac();
            for (const auto& a : g_acs)
            {
                Ptr<QosTxop> txop = staMac->GetQosTxop(a.ac);
                txop->SetAifsn(a.aifsn);
                txop->SetMinCw(a.cwMin);
                txop->SetMaxCw(a.cwMax);
                if (!defaultTxop)
                {
                    txop->SetTxopLimit(Time(0));
                }
            }
            staMac->TraceConnectWithoutContext("DroppedMpdu", MakeCallback(&StaDroppedMpduSink));
            staMac->TraceConnectWithoutContext("MpduResponseTimeout",
                                               MakeBoundCallback(&AckTimeoutSink, false));
        }
    }

    // ------------------------------------------------------------ IP
    InternetStackHelper stack;
    stack.Install(apNode);
    stack.Install(staNodes);
    Ipv4AddressHelper addr("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer apIf = addr.Assign(apDev);
    Ipv4InterfaceContainer staIf = addr.Assign(staDevs);
    // Static ARP entries instead of ARP exchanges. The paper has no ARP, and
    // an ARP request of the AP travels through its AC_BE queue: once AC_VO and
    // AC_VI are saturated it starves there, the station is never resolved and
    // all its streams are dropped above the MAC without any MAC drop.
    NeighborCacheHelper neighborCache;
    neighborCache.PopulateNeighborCache();
    if (!qdisc)
    {
        // Assign() installs a default queue disc (FqCoDel per AC) above the MAC.
        // The paper has no such layer: packets go straight into the MAC queue
        // of their AC and are dropped there when it is full.
        TrafficControlHelper tch;
        tch.Uninstall(apDev);
        tch.Uninstall(staDevs);
        apNode.Get(0)->GetObject<TrafficControlLayer>()->TraceConnectWithoutContext(
            "TcDrop",
            MakeCallback(&TcDropSink));
        for (uint32_t i = 0; uplinkPose && i < nSta; ++i)
        {
            staNodes.Get(i)->GetObject<TrafficControlLayer>()->TraceConnectWithoutContext(
                "TcDrop",
                MakeCallback(&StaTcDropSink));
        }
    }

    // ------------------------------------------------------------ applications
    const Time tStart = Seconds(appStart);
    g_measStart = tStart + Seconds(warmup);
    g_measEnd = g_measStart + Seconds(measTime);

    if (!beacons)
    {
        // "Beacon frames are not generated" (paper). The stations associate
        // with the help of the beacons before the sources start.
        Simulator::Schedule(tStart, [apMac]() {
            apMac->SetAttribute("BeaconGeneration", BooleanValue(false));
        });
    }

    // frame phases of the burst streams, own RNG stream
    auto phaseRv = CreateObject<UniformRandomVariable>();
    phaseRv->SetStream(900);
    uint32_t burstFrags = 0;       // MSDUs per video frame (burst model)
    uint32_t burstLastMsdu = 0;    // size of the last MSDU of a frame [byte]

    stream = 1000;
    for (std::size_t k = 0; k < g_acs.size(); ++k)
    {
        const AcConfig& a = g_acs[k];
        const double streamRate = acLoad[k] * 1e6 / nSta; // [bit/s] per stream, MSDU level
        const bool burst = (a.ac == AC_VI && viModel == "burst");
        for (uint32_t i = 0; i < nSta; ++i)
        {
            const uint16_t port = 5000 + 10 * k + i;
            PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                        InetSocketAddress(Ipv4Address::GetAny(), port));
            ApplicationContainer sink = sinkHelper.Install(staNodes.Get(i));
            sink.Start(Seconds(0.0));
            sink.Get(0)->TraceConnectWithoutContext(
                "RxWithoutAddress",
                MakeBoundCallback(&RxSink, static_cast<int>(k), i));

            if (acLoad[k] <= 0)
            {
                continue; // this AC carries no traffic
            }

            auto app = CreateObject<XrTrafficApp>();
            auto size = CreateObject<ConstantRandomVariable>();
            Time start = tStart;
            if (burst)
            {
                // Periodic video frames. A frame of B MSDU bytes is split into
                // n = ceil(B / msduSize) MSDUs, all full except the last one.
                // The app counts frame sizes in UDP payload bytes.
                const double frameBytes = streamRate / (8.0 * viFps); // MSDU bytes per frame
                const auto n = static_cast<uint32_t>(std::ceil(frameBytes / msduSize - 1e-9));
                const double udpBytes = frameBytes - n * g_overhead;
                const double last = udpBytes - (n - 1.0) * payload;
                NS_ABORT_MSG_IF(n < 1 || last < XrHeader::SIZE,
                                "burst: last MSDU of a frame would be smaller than the "
                                "XrHeader, choose another load or frame rate");
                burstFrags = n;
                burstLastMsdu = static_cast<uint32_t>(std::lround(last)) + g_overhead;
                size->SetAttribute("Constant", DoubleValue(udpBytes));
                app->SetAttribute("ArrivalProcess", EnumValue(XrTrafficApp::PERIODIC));
                app->SetAttribute("FrameRate", DoubleValue(viFps));
                app->SetAttribute("MaxPayloadSize", UintegerValue(payload));
                if (viPhase == "random")
                {
                    start += Seconds(phaseRv->GetValue(0.0, 1.0 / viFps));
                }
            }
            else
            {
                // one MSDU per arrival, exponential inter-arrival times
                size->SetAttribute("Constant", DoubleValue(payload));
                app->SetAttribute("ArrivalProcess", EnumValue(XrTrafficApp::POISSON));
                app->SetAttribute("FrameRate", DoubleValue(streamRate / (8.0 * msduSize)));
                app->SetAttribute("MaxPayloadSize", UintegerValue(payload));
            }
            app->SetAttribute("Remote",
                              AddressValue(InetSocketAddress(staIf.GetAddress(i), port)));
            app->SetAttribute("Tos", UintegerValue(a.tos));
            app->SetAttribute("FrameSize", PointerValue(size));
            app->SetStartTime(start);
            app->SetStopTime(g_measEnd);
            apNode.Get(0)->AddApplication(app);
            stream += app->AssignStreams(stream);
            app->TraceConnectWithoutContext(
                "PacketTx",
                MakeBoundCallback(&PacketTxSink, static_cast<int>(k), i));
            app->TraceConnectWithoutContext(
                "FrameTx",
                MakeBoundCallback(&FrameTxSink, static_cast<int>(k)));
        }
    }

    // ------------------------------------------------------------ uplink pose
    // Own RNG streams (phase 901, sources from 2000), so that the downlink
    // sources draw the same random numbers with and without the uplink.
    if (uplinkPose)
    {
        auto posePhaseRv = CreateObject<UniformRandomVariable>();
        posePhaseRv->SetStream(901);
        int64_t poseStream = 2000;
        for (uint32_t i = 0; i < nSta; ++i)
        {
            const uint16_t port = 6000 + i;
            PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                        InetSocketAddress(Ipv4Address::GetAny(), port));
            ApplicationContainer sink = sinkHelper.Install(apNode.Get(0));
            sink.Start(Seconds(0.0));
            sink.Get(0)->TraceConnectWithoutContext("RxWithoutAddress",
                                                    MakeBoundCallback(&RxSink, g_poseSlot, i));

            auto app = CreateObject<XrTrafficApp>();
            auto size = CreateObject<ConstantRandomVariable>();
            size->SetAttribute("Constant", DoubleValue(posePayload));
            app->SetAttribute("ArrivalProcess", EnumValue(XrTrafficApp::PERIODIC));
            app->SetAttribute("FrameRate", DoubleValue(poseRateHz));
            app->SetAttribute("MaxPayloadSize", UintegerValue(posePayload));
            app->SetAttribute("Remote",
                              AddressValue(InetSocketAddress(apIf.GetAddress(0), port)));
            app->SetAttribute("Tos", UintegerValue(0xc0)); // UP 6 -> AC_VO
            app->SetAttribute("FrameSize", PointerValue(size));
            // the stations are independent devices: independent pose phases
            app->SetStartTime(tStart + Seconds(posePhaseRv->GetValue(0.0, 1.0 / poseRateHz)));
            app->SetStopTime(g_measEnd);
            staNodes.Get(i)->AddApplication(app);
            poseStream += app->AssignStreams(poseStream);
            app->TraceConnectWithoutContext("PacketTx",
                                            MakeBoundCallback(&PacketTxSink, g_poseSlot, i));
            app->TraceConnectWithoutContext("FrameTx",
                                            MakeBoundCallback(&FrameTxSink, g_poseSlot));
        }
    }

    if (verbose)
    {
        std::cout << "=== EDCA Fig. 8 baseline (A4) ===\n"
                  << "offered load per AC [Mb/s]: VO " << acLoad[0] << ", VI " << acLoad[1]
                  << ", BE " << acLoad[2] << ", BK " << acLoad[3] << " (" << nSta
                  << " streams per AC), MSDU " << msduSize << " B (UDP payload " << payload
                  << " B)\n"
                  << "AC_VI arrival process: " << viModel;
        if (viModel == "burst")
        {
            std::cout << ", " << viFps << " frames/s per stream, " << burstFrags
                      << " MSDUs per frame (last one " << burstLastMsdu << " B), phases "
                      << viPhase;
        }
        if (uplinkPose)
        {
            std::cout << "\nuplink pose: " << nSta << " stations, AC_VO, " << posePayload
                      << " B payload every " << 1e3 / poseRateHz << " ms, Table 1 on the stations";
        }
        std::cout << "\n802.11a, all frames " << dataMode << ", distance " << distance
                  << " m, seed 1, run " << run << "\n"
                  << "sources start " << appStart << " s, warm-up " << warmup << " s, measured "
                  << measTime << " s, beacons during the measurement: " << (beacons ? "yes" : "no")
                  << "\n"
                  << "MAC queue " << queueSize << ", lifetime " << queueDelayMs
                  << " ms, retry limit " << retryLimit << ", queue disc "
                  << (qdisc ? "default" : "none") << "\n"
                  << "AC      AIFSN  CWmin  CWmax  TXOPlimit\n";
        for (const auto& a : g_acs)
        {
            Ptr<QosTxop> t = apMac->GetQosTxop(a.ac);
            std::cout << std::left << std::setw(8) << a.name << std::setw(7)
                      << static_cast<uint32_t>(t->GetAifsn(SINGLE_LINK_OP_ID)) << std::setw(7)
                      << t->GetMinCw(SINGLE_LINK_OP_ID) << std::setw(7)
                      << t->GetMaxCw(SINGLE_LINK_OP_ID)
                      << t->GetTxopLimit(SINGLE_LINK_OP_ID).As(Time::US) << "\n";
        }
    }

    if (!arrivalFile.empty())
    {
        if (const auto dir = std::filesystem::path(arrivalFile).parent_path(); !dir.empty())
        {
            std::filesystem::create_directories(dir);
        }
        g_arrivalLog.open(arrivalFile);
        NS_ABORT_MSG_IF(!g_arrivalLog, "Cannot open " << arrivalFile);
        g_arrivalLog << "ac,stream,frame_id,time_ns,msdu_bytes\n";
    }

    Simulator::Stop(g_measEnd);
    Simulator::Run();
    g_arrivalLog.close();

    // ------------------------------------------------------------ results
    const bool newFile = !std::filesystem::exists(outFile) || std::filesystem::file_size(outFile) == 0;
    if (const auto dir = std::filesystem::path(outFile).parent_path(); !dir.empty())
    {
        std::filesystem::create_directories(dir);
    }
    std::ofstream os(outFile, std::ios::app);
    NS_ABORT_MSG_IF(!os, "Cannot open " << outFile);
    if (newFile)
    {
        os << "tag,load_mbps,run,vi_model,ac,offered_mbps,throughput_mbps,tx_pkts,rx_pkts,"
              "mean_delay_ms,std_delay_ms,drop_queue,drop_lifetime,drop_retry,"
              "tx_frames,rx_frames,mean_frame_delay_ms,queue_pkts"
           << (uplinkPose ? ",ack_timeouts" : "") << '\n';
    }
    const std::string model = viModel == "burst" ? "burst-" + viPhase : viModel;
    if (verbose)
    {
        std::cout << "\nAC      offered  thrpt   delay    drops: queue  lifetime  retry"
                  << (uplinkPose ? "  ACK timeouts" : "") << "\n"
                  << "        [Mb/s]   [Mb/s]  [ms]\n";
    }
    double total = 0; // downlink only
    const std::size_t nRows = g_acs.size() + (uplinkPose ? 1 : 0);
    for (std::size_t k = 0; k < nRows; ++k)
    {
        const AcStats& s = g_stats[k];
        const double offered = s.txBytes * 8.0 / measTime / 1e6;
        const double thr = s.rxBytes * 8.0 / measTime / 1e6;
        const double mean = s.rxPkts ? s.delaySum / s.rxPkts : 0.0;
        const double var = s.rxPkts > 1
                               ? std::max(0.0,
                                          (s.delaySqSum - s.rxPkts * mean * mean) /
                                              (s.rxPkts - 1))
                               : 0.0;
        const double frameMean = s.rxFrames ? s.frameDelaySum / s.rxFrames : 0.0;
        total += k < g_acs.size() ? thr : 0.0;
        os << tag << ',' << load << ',' << run << ',' << model << ',' << RowName(k) << ','
           << std::fixed
           << std::setprecision(6) << offered << ',' << thr << ',' << s.txPkts << ',' << s.rxPkts
           << ',' << mean * 1e3 << ',' << std::sqrt(var) * 1e3 << ',' << s.dropQueue << ','
           << s.dropLifetime << ',' << s.dropRetry << ',' << s.txFrames << ',' << s.rxFrames
           << ',' << frameMean * 1e3 << ',' << QueueSize(queueSize).GetValue();
        if (uplinkPose)
        {
            os << ',' << g_ackTimeouts[k];
        }
        os << '\n';
        os.unsetf(std::ios::fixed);
        os << std::setprecision(6);
        if (verbose)
        {
            std::cout << std::left << std::setw(8) << RowName(k) << std::fixed
                      << std::setprecision(3) << std::setw(9) << offered << std::setw(8) << thr
                      << std::setw(16) << mean * 1e3 << std::setw(7) << s.dropQueue
                      << std::setw(10) << s.dropLifetime << std::setw(7) << s.dropRetry;
            if (uplinkPose)
            {
                std::cout << g_ackTimeouts[k];
            }
            std::cout << "\n";
            std::cout.unsetf(std::ios::fixed);
        }
    }
    if (verbose)
    {
        std::cout << "total downlink throughput " << std::fixed << std::setprecision(3) << total
                  << " Mb/s -> " << outFile << "\n";
    }

    if (!delayFile.empty())
    {
        if (const auto dir = std::filesystem::path(delayFile).parent_path(); !dir.empty())
        {
            std::filesystem::create_directories(dir);
        }
        std::ofstream ds(delayFile);
        NS_ABORT_MSG_IF(!ds, "Cannot open " << delayFile);
        ds << "load_mbps,run,vi_model,ac,kind,bin_upper_us,count\n";
        for (std::size_t k = 0; k < nRows; ++k)
        {
            std::ostringstream prefix;
            prefix << load << ',' << run << ',' << model << ',' << RowName(k);
            g_stats[k].pktDelay.Write(ds, prefix.str() + ",packet");
            g_stats[k].frameDelay.Write(ds, prefix.str() + ",frame");
        }
    }

    Simulator::Destroy();
    return 0;
}
