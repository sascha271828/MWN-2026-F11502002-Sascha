#include "xr-traffic-app.h"

#include "xr-header.h"

#include "ns3/double.h"
#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/pointer.h"
#include "ns3/simulator.h"
#include "ns3/socket.h"
#include "ns3/string.h"
#include "ns3/udp-socket-factory.h"
#include "ns3/uinteger.h"

#include <algorithm>
#include <cmath>

namespace ns3
{

NS_LOG_COMPONENT_DEFINE("XrTrafficApp");
NS_OBJECT_ENSURE_REGISTERED(XrTrafficApp);

TypeId
XrTrafficApp::GetTypeId()
{
    static TypeId tid =
        TypeId("ns3::XrTrafficApp")
            .SetParent<SourceApplication>()
            .SetGroupName("Applications")
            .AddConstructor<XrTrafficApp>()
            .AddAttribute("FrameRate",
                          "Frame generation rate F of the nominal periodic grid [Hz].",
                          DoubleValue(60.0),
                          MakeDoubleAccessor(&XrTrafficApp::m_frameRate),
                          MakeDoubleChecker<double>(0.001))
            .AddAttribute("FrameSize",
                          "Random variable for the frame size [byte].",
                          StringValue("ns3::ConstantRandomVariable[Constant=1000]"),
                          MakePointerAccessor(&XrTrafficApp::m_frameSize),
                          MakePointerChecker<RandomVariableStream>())
            .AddAttribute("Jitter",
                          "Random variable for the jitter added to the nominal frame time [ms].",
                          StringValue("ns3::ConstantRandomVariable[Constant=0]"),
                          MakePointerAccessor(&XrTrafficApp::m_jitter),
                          MakePointerChecker<RandomVariableStream>())
            .AddAttribute("MaxPayloadSize",
                          "Maximum UDP payload per packet incl. the 16 B XrHeader [byte]. "
                          "1472 B fits a 1500 B IP MTU.",
                          UintegerValue(1472),
                          MakeUintegerAccessor(&XrTrafficApp::m_maxPayload),
                          MakeUintegerChecker<uint32_t>(XrHeader::SIZE + 1))
            .AddTraceSource("FrameTx",
                            "A frame was generated and handed to the socket.",
                            MakeTraceSourceAccessor(&XrTrafficApp::m_frameTxTrace),
                            "ns3::XrTrafficApp::FrameTxCallback")
            .AddTraceSource("PacketTx",
                            "A fragment (UDP payload) of a frame was sent.",
                            MakeTraceSourceAccessor(&XrTrafficApp::m_packetTxTrace),
                            "ns3::XrTrafficApp::PacketTxCallback");
    return tid;
}

XrTrafficApp::XrTrafficApp()
    : SourceApplication(false) // UDP over IP only, no packet sockets
{
    NS_LOG_FUNCTION(this);
    m_protocolTid = UdpSocketFactory::GetTypeId();
}

XrTrafficApp::~XrTrafficApp()
{
    NS_LOG_FUNCTION(this);
}

int64_t
XrTrafficApp::AssignStreams(int64_t stream)
{
    NS_LOG_FUNCTION(this << stream);
    m_frameSize->SetStream(stream);
    m_jitter->SetStream(stream + 1);
    return 2;
}

void
XrTrafficApp::DoDispose()
{
    NS_LOG_FUNCTION(this);
    m_frameSize = nullptr;
    m_jitter = nullptr;
    SourceApplication::DoDispose();
}

void
XrTrafficApp::DoStartApplication()
{
    NS_LOG_FUNCTION(this);
    m_period = Seconds(1.0 / m_frameRate);
    m_socket->ShutdownRecv();
    // UDP connects synchronously, so m_connected is already true here.
    // The base class cancels events right before calling this method.
    if (m_connected)
    {
        m_gridStart = Simulator::Now();
        m_tickEvent = Simulator::ScheduleNow(&XrTrafficApp::Tick, this);
    }
}

void
XrTrafficApp::DoConnectionSucceeded(Ptr<Socket> socket)
{
    NS_LOG_FUNCTION(this << socket);
    // Nothing to do: for UDP the generator is started in DoStartApplication().
}

void
XrTrafficApp::CancelEvents()
{
    NS_LOG_FUNCTION(this);
    m_tickEvent.Cancel();
    for (auto& ev : m_frameEvents)
    {
        ev.Cancel();
    }
    m_frameEvents.clear();
}

void
XrTrafficApp::Tick()
{
    NS_LOG_FUNCTION(this);

    // drop bookkeeping of frame events that already fired
    while (!m_frameEvents.empty() && m_frameEvents.front().IsExpired())
    {
        m_frameEvents.pop_front();
    }

    // Frame k = m_nextFrameId has nominal time t_start + (k+1)/F.
    // It is scheduled one period ahead so that negative jitter down to -1/F
    // can be represented without scheduling into the past.
    const uint32_t frameId = m_nextFrameId++;
    const Time nominal = m_gridStart + m_period * static_cast<int64_t>(frameId + 1);
    // NOTE: MilliSeconds() only has integer overloads, it would truncate the jitter
    const Time jitter = Time::FromDouble(m_jitter->GetValue(), Time::MS);
    Time delay = nominal + jitter - Simulator::Now();
    if (delay.IsStrictlyNegative())
    {
        NS_LOG_WARN("Jitter " << jitter.As(Time::MS) << " exceeds one frame period, clamped");
        delay = Time(0);
    }
    m_frameEvents.push_back(
        Simulator::Schedule(delay, &XrTrafficApp::SendFrame, this, frameId, nominal));

    // next tick exactly on the nominal grid (no drift)
    m_tickEvent = Simulator::Schedule(nominal - Simulator::Now(), &XrTrafficApp::Tick, this);
}

void
XrTrafficApp::SendFrame(uint32_t frameId, Time nominal)
{
    NS_LOG_FUNCTION(this << frameId);

    // frame size, at least one header worth of bytes
    const double drawn = m_frameSize->GetValue();
    const auto frameSize =
        std::max<uint32_t>(static_cast<uint32_t>(std::lround(drawn)), XrHeader::SIZE);

    const uint32_t nFrags = (frameSize + m_maxPayload - 1) / m_maxPayload;
    NS_ABORT_MSG_IF(nFrags > 0xFFFF, "Frame too large for the 16 bit fragment counter");

    m_frameTxTrace(frameId, frameSize, nominal);
    ++m_framesSent;

    XrHeader hdr;
    hdr.SetFrameId(frameId);
    hdr.SetNFrags(static_cast<uint16_t>(nFrags));
    hdr.SetTxTime(Simulator::Now());

    uint32_t remaining = frameSize;
    for (uint32_t i = 0; i < nFrags; ++i)
    {
        // fill to MaxPayloadSize, last fragment carries the remainder
        // (padded up to the header size if the remainder is smaller)
        const uint32_t payload = std::max(std::min(remaining, m_maxPayload), XrHeader::SIZE);
        remaining -= std::min(remaining, m_maxPayload);

        hdr.SetFragIdx(static_cast<uint16_t>(i));
        Ptr<Packet> p = Create<Packet>(payload - XrHeader::SIZE);
        p->AddHeader(hdr);

        if (m_socket->Send(p) >= 0)
        {
            ++m_packetsSent;
            m_txTrace(p);
            m_packetTxTrace(frameId, static_cast<uint16_t>(i), payload);
        }
        else
        {
            ++m_sendFailures;
            NS_LOG_WARN("Send failed for frame " << frameId << " fragment " << i);
        }
    }
}

} // namespace ns3