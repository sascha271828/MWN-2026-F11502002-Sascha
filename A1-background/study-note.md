# <center>A1 — Background Study Notes</center>

- [A1 — Background Study Notes](#a1--background-study-notes)
  - [1. Five-minute presentation](#1-five-minute-presentation)
    - [1.1 Keep it simple](#11-keep-it-simple)
    - [1.2 Never read from your slides](#12-never-read-from-your-slides)
    - [1.3 Use beautiful photos](#13-use-beautiful-photos)
    - [1.4 Keep data simple](#14-keep-data-simple)
    - [1.5 Repetition](#15-repetition)
  - [2. How to Read a Paper](#2-how-to-read-a-paper)
    - [2.1 Three-pass approach](#21-three-pass-approach)
      - [First pass](#first-pass)
      - [Second pass](#second-pass)
      - [Third pass](#third-pass)
    - [2.2 Literature survey](#22-literature-survey)
    - [2.3 Related work](#23-related-work)
  - [3. Reading the paper for the basic path](#3-reading-the-paper-for-the-basic-path)
    - [3.1 First pass](#31-first-pass)
    - [3.2 Second pass](#32-second-pass)
      - [Legacy 802.11](#legacy-80211)
      - [802.11e](#80211e)
      - [Evaluation](#evaluation)
      - [Summary and conclusion](#summary-and-conclusion)
    - [3.3 Third Pass](#33-third-pass)
  - [4. Project proposal](#4-project-proposal)
    - [4.1 Path and paper](#41-path-and-paper)
    - [4.2 Problem](#42-problem)
    - [4.3 Baseline to reproduce](#43-baseline-to-reproduce)
    - [4.4 What I would measure](#44-what-i-would-measure)
    - [4.5 Planned modification](#45-planned-modification)
    - [4.6 Open questions](#46-open-questions)

## 1. Five-minute presentation

*[Video](https://www.youtube.com/watch?v=YVgS_opYacQ): 5 Tips about Presentation Slides in 5 min, Undergraduate Library, University of North Carolina at Chapel Hill, 2017.*

### 1.1 Keep it simple

- Avoid the generic templates everybody has seen before. The audience recognises them and assumes it already knows what is coming.
- Avoid cluttered or distracting designs that pull attention away from the content and towards the design itself.

*The reasoning behind the template argument was not really explained in the video, so I am taking it as a rule of thumb rather than a fact.*

### 1.2 Never read from your slides

- The brain is bad at processing spoken and written text at the same time. If the slide carries the full text, the audience reads it instead of listening.
- Use as few words as possible, as many as necessary.
- Use a font that is easy to read, and set the text large.
- One point per slide, so the focus stays on the topic currently being covered instead of the next one.

*This part of the video was the weakest. It is poorly structured and the title does not really match what is discussed.*

### 1.3 Use beautiful photos

- Photos carry emotion and can do work that text cannot.
- Keep copyright in mind when picking images.
- Images should be large and of sufficient resolution, otherwise they look cheap or become unreadable.
- Consider the rule of thirds: place the focal point at about 1/3 or 2/3 of the width or height.

*The copyright point is more nuanced than the video suggests. A presentation held in a classroom and a commercially broadcast presentation are not treated the same way under fair use or the equivalent national rules.*

### 1.4 Keep data simple

- Avoid overly complex graphs that are hard to read in a few seconds.
- Build graphs that emphasise the one point the slide is making, and strip the rest.

### 1.5 Repetition

- Keep the design consistent across all slides.
- Do not mix several fonts or several colour palettes.
- Keep the palette small, roughly two to three colours.
- Reuse the same layouts.

## 2. How to Read a Paper

*[Document](https://web.stanford.edu/class/ee384m/Handouts/HowtoReadPaper.pdf) by S. Keshav, David R. Cheriton School of Computer Science, University of Waterloo, ON, Canada.*

### 2.1 Three-pass approach

Reading a paper in several passes, each going deeper and building on the previous one, avoids having to force yourself through the whole text from start to finish multiple times.

#### First pass

*Goal: get a general idea of the paper.*

Read the following:

1. Title, abstract, introduction
2. Section and subsection headings only
3. Conclusion
4. Skim the references and tick off the ones already read

Then decide whether the paper is worth reading, using the *five Cs*:

1. *Category*: what type of paper is this (measurement paper, analysis of an existing system, description of a research prototype)?
2. *Context*: which other papers is it related to, and which theoretical bases are used to analyse the problem?
3. *Correctness*: do the assumptions appear to be valid?
4. *Contributions*: what are the paper's main contributions?
5. *Clarity*: is the paper well written?

A paper should be structured so that reviewers and readers get the gist within about five minutes, because that is all the attention many of them will give it.

#### Second pass

*Goal: understand the content, but not yet the details.*

- Read the paper, but skip technical details such as proofs.
- Write down comments and key points while reading.
- Look carefully at figures, diagrams and illustrations: are the axes labelled, are error bars included, is statistical significance addressed?
- Mark relevant unread references for later reading.

The second pass can take up to an hour. Afterwards you should be able to summarise the paper's content with supporting evidence. This depth is good enough for a paper that interests me but is not part of my own research.

If the paper still does not make sense:

- Set it aside and hope it will not matter for my career.
- Come back to it later, after more background reading.
- Or go to the third pass.

#### Third pass

*Goal: understand the paper in depth, including details.*

- Virtually re-implement the paper: make the same assumptions as the authors and recreate their work.
- Identify and challenge every assumption in every statement.
- Compare how I would have presented an idea with how the authors did it.

A third pass takes roughly four to five hours for a beginner and about an hour for an experienced reader. Afterwards you should be able to reconstruct the structure of the paper from memory and point out its strong and weak points.

### 2.2 Literature survey

Reading into a field I am not familiar with, to build an overview of the topic.

1. Use an academic search engine (Google Scholar, CiteSeer) with well chosen keywords.
   - Do a first pass on the hits.
   - Read their related work sections.
   - If a recent survey paper exists, that is the shortcut and the survey is largely the answer.
2. Identify citations and author names that keep reappearing. These point to the key authors and key papers of the field, and through them to the major conferences.
3. Check the websites of those top conferences for recent high-quality work.
   - Do a second pass on those papers and on the key papers identified earlier.
   - If they keep citing a paper that is not yet on the list, read that one too.

### 2.3 Related work

- *Writing reviews*: Timothy Roscoe, ["Writing reviews for systems conferences"](https://people.inf.ethz.ch/troscoe/pubs/review-writing.pdf)
- *Writing technical papers*: Henning Schulzrinne's [website](https://www.cs.columbia.edu/~hgs/etc/writing-style.html) and George Whitesides' [overview](https://intra.ece.ucr.edu/~rlake/Whitesides_writing_res_paper.pdf) of the process
- *General research skills*: Simon Peyton Jones' [website](https://simon.peytonjones.org/research-skills/)

## 3. Reading the paper for the basic path

*Applying the three-pass approach to S. Mangold et al., ["Analysis of IEEE 802.11e for QoS Support in Wireless LANs"](https://ieeexplore.ieee.org/document/1265851), IEEE Wireless Communications, December 2003.*

### 3.1 First pass

Answering the *five Cs*:

1. *Category*

   A protocol analysis combined with a simulation-based evaluation. It is not a measurement paper and not a prototype description.

2. *Context*

   It analyses the then upcoming IEEE 802.11e amendment and compares it against legacy IEEE 802.11, with the focus on QoS support. It builds on the authors' earlier 802.11e evaluations and on the 802.11e draft standard itself.

3. *Correctness*

   The protocol description rests on the IEEE draft, so that part is solid. The assumptions sit in the evaluation rather than in the protocol discussion: a simplified traffic model (512 byte MSDUs, negative exponential inter-arrival times, 250 kb/s per stream), fixed PHY rates (24 Mb/s for data, 6 Mb/s for control), no RTS/CTS, no fragmentation, no hidden stations, and no beacon frames. Those are reasonable for isolating the MAC behaviour, but they mean the absolute numbers cannot be read as real-world performance.

4. *Contributions*

   It explains the QoS mechanisms introduced by 802.11e (EDCA and HCCA), and quantifies with simulations how well they prioritise traffic compared to legacy 802.11, including the case of overlapping QBSSs.

5. *Clarity*

   The structure is coherent and logical. Skimming alone gave me a good idea of what the paper wants to show.

*Conclusion*: worth reading, since it is the shortest path to understanding 802.11e, and it is the assigned paper for the basic path anyway.

### 3.2 Second pass

*Short summary of the main points, in my own words.*

#### Legacy 802.11

- Legacy 802.11 uses CSMA/CA. The distributed coordination function (DCF) provides contention-based access with no QoS differentiation.
- QoS support is only available through the point coordination function (PCF), which offers time-bounded services centrally controlled by the point coordinator (PC), normally located in the AP.
- A superframe starts with a beacon frame at the target beacon transmission time (TBTT). Beacons synchronise the local timers of the stations and distribute protocol parameters.

Limitations:

- The PC must wait for an idle medium plus a PIFS before sending the beacon (PIFS is shorter than DIFS, so the PC has priority, but not immediate access). The beacon can therefore be delayed past the TBTT, in 802.11a by up to about 4.9 ms in the worst case. That delay propagates into every contention-free period (CFP) and makes the delay of time-bounded traffic unpredictable.
- The transmission time of a polled station is not under the control of the PC. A polled station may send an MSDU of arbitrary length, up to 2304 bytes, fragmented, and with any of the supported modulation and coding schemes. The remaining stations polled later in the CFP lose QoS because of it.

#### 802.11e

802.11e introduces the hybrid coordination function (HCF), which combines DCF and PCF ideas, hence "hybrid". It defines two access mechanisms:

- Contention-based channel access: enhanced distributed channel access (EDCA), used in the contention period (CP) only.
- Controlled channel access: HCF controlled channel access (HCCA), used in both CP and CFP.

The central coordinator is the hybrid coordinator (HC), which sits in the 802.11e AP. A BSS with an HC is called a QBSS. Because a station runs several backoff processes in parallel, the paper talks about *backoff entities* rather than stations.

**Basic improvements over legacy 802.11**

- A backoff entity that gains access must not occupy the medium longer than a given limit. This interval is the transmission opportunity (TXOP), defined by a start time and a duration.
  - Obtained by contention: EDCA-TXOP, bounded by the QBSS-wide *TXOPlimit* that the HC distributes in the beacon.
  - Obtained by the HC through controlled access: HCCA-TXOP, also called polled TXOP.
- No backoff entity transmits across the TBTT. A frame exchange starts only if it can finish before the next TBTT, which reduces the beacon delay and gives the HC better control of the medium.
- A backoff entity may transmit directly to another backoff entity in the same QBSS, without relaying through the AP, using the direct link protocol (DLP).

**HCF contention-based access (EDCA)**

- Four access categories (ACs), one backoff entity each, named after their target traffic: AC_VO (voice), AC_VI (video), AC_BE (best effort), AC_BK (background). The eight 802.1D user priorities are mapped onto these four ACs.
- Priorities come from the AC-specific EDCA parameter set. The HC defines it, announces it in beacon frames, and may change it over time. All stations in the QBSS must use the same values.
- A backoff entity starts counting down its backoff counter after the medium has been idle for the arbitration interframe space AIFS[AC], instead of DIFS:

  $AIFS[AC] = SIFS + AIFSN[AC] \cdot aSlotTime, \;\; AIFSN[AC] \geq 2$

  AIFS[AC] is at least DIFS. The smaller the AIFSN[AC], the higher the priority. The HC should choose AIFSN[AC] so that the earliest access time of EDCA stations equals DIFS, which keeps them compatible with legacy stations.
- CWmin[AC] and CWmax[AC] are also per AC. Smaller values mean higher priority but a higher collision probability. With AIFS equal to DIFS, priority over legacy stations requires CWmin[AC] < 15 in 802.11a.
- Default values used in the paper (Table 1), in the order AC_VO / AC_VI / AC_BE / AC_BK: AIFSN 2 / 2 / 3 / 7, CWmin 3 / 7 / 15 / 15, CWmax 7 / 15 / 1023 / 1023.
- TXOPlimit[AC] is part of the parameter set as well. A larger limit means a larger share of capacity, because the entity may send several MSDUs back to back within the same TXOP (continuation of an EDCA-TXOP).
- 802.11e also defines a maximum MSDU lifetime per AC. A frame that has waited longer than that in the MAC is dropped instead of transmitted, which makes sense for real-time traffic where a late frame is useless.
- If two backoff entities inside the same station reach zero in the same slot, a virtual collision occurs: the higher-priority entity transmits, the others behave as if a collision had happened on the medium.

**HCF controlled access (HCCA)**

- The HC may allocate a TXOP to itself after sensing the medium idle for PIFS, without any backoff, in both CP and CFP. This is why AIFSN[AC] must be chosen so that no EDCA station can access the medium earlier than DIFS.
- During the CP, a station gets a TXOP either through the EDCA rules or when it receives a QoS CF-Poll from the HC.
- During the CFP, stations never access the medium unless polled. Only the HC allocates TXOPs, by sending QoS CF-Poll frames or by transmitting downlink data directly.
- Within a polled TXOP, the station may send several frames separated by SIFS, as long as the whole exchange stays within the allocated TXOPlimit.
- A polled TXOP can still be delayed by an EDCA-TXOP that is already running, which is why the HC controls the TXOPlimit of the whole QBSS.

**Improved efficiency**

- Block acknowledgment: several MPDUs are acknowledged by a single block ACK instead of one ACK per MPDU.
- Direct link protocol: direct station-to-station traffic inside the QBSS, without the detour via the AP.

#### Evaluation

Simulation setup, event-driven with an 802.11a PHY model:

- Data frames at 24 Mb/s, control frames at 6 Mb/s, stations not hidden from each other.
- 512 byte MSDUs with negative exponentially distributed inter-arrival times, 250 kb/s per stream.
- No RTS/CTS, no fragmentation, no beacon frames, one data frame per EDCA-TXOP.

Results:

- *Throughput in an isolated QBSS with four stations* (Fig. 8): the AP sends four streams, one per AC, to each of three stations, twelve streams in total. With increasing offered traffic, the higher-priority ACs keep their throughput and suppress the lower ones, thanks to their smaller AIFSN, CWmin and CWmax. The prioritisation works as intended.
- *Throughput with increasing number of stations* (Fig. 9): up to 16 stations, each offering 1 Mb/s split over all four ACs. Throughput collapses once many stations contend, and AC_VO degrades fastest because its small CWmin and CWmax make collisions more likely. The paper notes that this is a parameter problem, not a protocol problem: the HC can and should adapt the EDCA parameter set, and in practice AC_VO would carry far less traffic per station, typically a single voice call.
- *Delay with prioritised HC access* (Fig. 10): the AP additionally carries an isochronous downstream over HCCA, which outranks every EDCA category. In an isolated QBSS the EDCA delays grow unpredictably with offered traffic, while the HCCA delays stay below a bound set by the TXOPlimit, here targeted at 300 µs.
- *Overlapping QBSSs* (Fig. 10): when two QBSSs interfere, even the polled high-priority stream exceeds the delay bound, because the two HCs share the medium without any coordination. In the worst case both HCs poll at the same time, all poll frames collide and the HCCA throughput drops to zero.

#### Summary and conclusion

- 802.11e provides effective QoS support in WLANs through EDCA (relative prioritisation) and HCCA (bounded delay), for a wide range of applications.
- The EDCA default parameters do not scale to many stations. The HC has to adapt the parameter set according to the traffic conditions.
- The overlapping QBSS problem remains open. 


### 3.3 Third Pass

I deliberately stopped after the second pass. 
A third pass means virtually re-implementing the paper and challenging every assumption in it, and I do not yet have the background in 802.11 MAC behaviour or in ns-3 to do that honestly.
In my understanding this will be part of A3 and A4.



 
## 4. Project proposal

*First draft.*

### 4.1 Path and paper

I am taking the **basic path**, working from the assigned paper: 
S. Mangold et al., "Analysis of IEEE 802.11e for QoS Support in Wireless LANs", IEEE Wireless Communications, December 2003.

### 4.2 Problem

802.11e provides QoS in a WLAN by splitting traffic into four access categories and giving each of them its own contention parameters. 
The paper shows that this prioritisation works: under increasing load, the high priority categories keep their throughput while best effort and background are squeezed out.

That result is produced with a deliberately simple traffic model. 
Every stream carries 250 kb/s in 512 byte MSDUs with negative exponentially distributed inter-arrival times, which the authors chose so that the traffic characteristics would not distort the MAC behaviour they wanted to isolate. 
Real multimedia traffic does not look like that. 
A video or XR stream arrives in bursts tied to a frame rate, with a packet size distribution that is far from constant and inter-arrival times that are strongly correlated.

So the question I want to answer is:  
**Does the prioritisation between access categories still behave the way the paper shows when the high priority traffic is a realistic multimedia stream instead of a memoryless one?**

### 4.3 Baseline to reproduce

Figure 8 of the paper: throughput per access category against offered traffic
per access category.

- Topology: one AP and three stations, no mobility, no hidden stations
- Traffic: the AP transmits four downlink streams to each station, one per AC,
  250 kb/s each, 512 byte MSDUs, exponential inter-arrival times. Twelve streams
  in total.
- PHY and MAC: 802.11a, data frames at 24 Mb/s, control frames at 6 Mb/s, no
  RTS/CTS, no fragmentation, one data frame per EDCA-TXOP, no beacon frames.
- EDCA parameter set from Table 1 of the paper: AIFSN 2 / 2 / 3 / 7, CWmin
  3 / 7 / 15 / 15, CWmax 7 / 15 / 1023 / 1023 for AC_VO / AC_VI / AC_BE / AC_BK.
- Expected result: the higher priority ACs restrain the throughput of the lower
  ones once the medium saturates.

### 4.4 What I would measure

- **Throughput per access category**, in Mb/s, as a function of offered load.
  This is the metric the baseline figure uses, so the comparison is direct.
- **MSDU delivery delay per access category**, as a distribution rather than a
  mean, since the interesting property of a QoS mechanism is the tail.
- **Frame loss**, split into collisions and frames dropped because the MSDU
  lifetime expired. Realistic bursty traffic should hit the lifetime limit more
  often than smooth traffic does, and that is the mechanism I expect to matter.

### 4.5 Planned modification

Replace the paper's synthetic traffic on the high priority categories with a
traffic model from 3GPP TS 26.926 (which will be covered in the course), keep best effort and background as they are,
and run the same sweep against the same baseline curves.


### 4.6 Open questions

- **Which stream type.** TS 26.926 covers several multimedia traffic types, and
  I do not yet know enough about them to pick one.
- **Rate scaling.** The 3GPP video and XR models generate tens of Mb/s, which
  alone saturates a 24 Mb/s 802.11a link. 
  Either I scale the model down to a
  rate comparable to the paper's 250 kb/s streams, or I raise the PHY rate and
  accept a deviation from the paper's settings.
- **Diffrent Simlutors.** The paper uses its own
  event-driven simulator, so absolute numbers will differ. 