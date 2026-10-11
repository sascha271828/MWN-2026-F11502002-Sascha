#include "xr-header.h"

#include "ns3/simulator.h"

namespace ns3
{

NS_OBJECT_ENSURE_REGISTERED(XrHeader);

TypeId
XrHeader::GetTypeId()
{
    static TypeId tid = TypeId("ns3::XrHeader")
                            .SetParent<Header>()
                            .SetGroupName("Applications")
                            .AddConstructor<XrHeader>();
    return tid;
}

TypeId
XrHeader::GetInstanceTypeId() const
{
    return GetTypeId();
}

XrHeader::XrHeader() = default;

void
XrHeader::SetFrameId(uint32_t id)
{
    m_frameId = id;
}

uint32_t
XrHeader::GetFrameId() const
{
    return m_frameId;
}

void
XrHeader::SetFragIdx(uint16_t idx)
{
    m_fragIdx = idx;
}

uint16_t
XrHeader::GetFragIdx() const
{
    return m_fragIdx;
}

void
XrHeader::SetNFrags(uint16_t n)
{
    m_nFrags = n;
}

uint16_t
XrHeader::GetNFrags() const
{
    return m_nFrags;
}

void
XrHeader::SetTxTime(Time t)
{
    m_txTimeNs = static_cast<uint64_t>(t.GetNanoSeconds());
}

Time
XrHeader::GetTxTime() const
{
    return NanoSeconds(static_cast<int64_t>(m_txTimeNs));
}

uint32_t
XrHeader::GetSerializedSize() const
{
    return SIZE;
}

void
XrHeader::Serialize(Buffer::Iterator start) const
{
    start.WriteHtonU32(m_frameId);
    start.WriteHtonU16(m_fragIdx);
    start.WriteHtonU16(m_nFrags);
    start.WriteHtonU64(m_txTimeNs);
}

uint32_t
XrHeader::Deserialize(Buffer::Iterator start)
{
    m_frameId = start.ReadNtohU32();
    m_fragIdx = start.ReadNtohU16();
    m_nFrags = start.ReadNtohU16();
    m_txTimeNs = start.ReadNtohU64();
    return SIZE;
}

void
XrHeader::Print(std::ostream& os) const
{
    os << "frame=" << m_frameId << " frag=" << m_fragIdx << "/" << m_nFrags
       << " tx=" << GetTxTime().As(Time::MS);
}

} // namespace ns3