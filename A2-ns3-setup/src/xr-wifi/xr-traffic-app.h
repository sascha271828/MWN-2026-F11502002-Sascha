/*
 * XrTrafficApp: generic periodic frame source following the statistical
 * XR traffic model of 3GPP TR 26.926 clause 6.5.3 (from TR 38.838).
 *
 * Model
 *   Frame k is generated at   t_k = t_start + (k+1)/F + J_k
 *   F    : FrameRate attribute [Hz]
 *   J_k  : Jitter random variable [ms], drawn independently per frame
 *   S_k  : FrameSize random variable [byte], drawn independently per frame
 *
 *   Jitter is applied on top of the NOMINAL periodic grid, so it does not
 *   accumulate. Each frame is split into UDP payloads of at most
 *   MaxPayloadSize bytes (filled to the maximum, last one carries the rest)
 *   and all fragments are sent back to back. Every payload starts with an
 *   XrHeader (16 B), which is counted inside the frame size.
 *
 * Reuse
 *   All model parameters are attributes. The same class is used for
 *     DL XR video : truncated normal FrameSize and Jitter, Tos 0xb8 (AC_VI)
 *     UL pose     : constant FrameSize, zero Jitter, Tos 0xc0 (AC_VO)
 *   Wi-Fi maps the 3 MSBs of the IP ToS to the user priority (TID).
 */
#ifndef XR_TRAFFIC_APP_H
#define XR_TRAFFIC_APP_H

#include "ns3/event-id.h"
#include "ns3/nstime.h"
#include "ns3/ptr.h"
#include "ns3/random-variable-stream.h"
#include "ns3/source-application.h"
#include "ns3/traced-callback.h"

#include <deque>

namespace ns3
{

class XrTrafficApp : public SourceApplication
{
  public:
    static TypeId GetTypeId();

    XrTrafficApp();
    ~XrTrafficApp() override;

    /**
     * Assign fixed random variable streams (for reproducible runs).
     * @param stream first stream index
     * @return number of streams assigned
     */
    int64_t AssignStreams(int64_t stream) override;

    /// Signature of the FrameTx trace: frame id, frame size [B], nominal time
    typedef void (*FrameTxCallback)(uint32_t frameId, uint32_t size, Time nominal);

    /// Signature of the PacketTx trace: frame id, fragment index, payload size [B]
    typedef void (*PacketTxCallback)(uint32_t frameId, uint16_t fragIdx, uint32_t size);

  protected:
    void DoDispose() override;

  private:
    void DoStartApplication() override;
    void DoConnectionSucceeded(Ptr<Socket> socket) override;
    void CancelEvents() override;

    /// Called on the nominal grid; schedules the jittered frame and the next tick
    void Tick();

    /// Draws the frame size, fragments the frame and sends it
    void SendFrame(uint32_t frameId, Time nominal);

    // attributes
    double m_frameRate;                   //!< frames per second [Hz]
    Ptr<RandomVariableStream> m_frameSize; //!< frame size [byte]
    Ptr<RandomVariableStream> m_jitter;    //!< jitter [ms]
    uint32_t m_maxPayload;                //!< max UDP payload per packet [byte]

    // state
    Time m_period;                  //!< 1 / FrameRate
    Time m_gridStart;               //!< reference of the nominal grid
    uint32_t m_nextFrameId{0};      //!< id of the next frame to schedule
    EventId m_tickEvent;            //!< next grid tick
    std::deque<EventId> m_frameEvents; //!< pending jittered frame events

    // statistics
    uint64_t m_framesSent{0};
    uint64_t m_packetsSent{0};
    uint64_t m_sendFailures{0};

    // traces
    TracedCallback<uint32_t, uint32_t, Time> m_frameTxTrace;
    TracedCallback<uint32_t, uint16_t, uint32_t> m_packetTxTrace;
};

} // namespace ns3

#endif // XR_TRAFFIC_APP_H