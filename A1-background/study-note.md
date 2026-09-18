# <center>A1 — Background Study Notes</center>

- [A1 — Background Study Notes](#a1--background-study-notes)
  - [1. Five-minute presentation](#1-five-minute-presentation)
    - [1.1 Keep it simple](#11-keep-it-simple)
    - [1.2 Never Read From your Slides](#12-never-read-from-your-slides)
    - [1.3 Use Beautiful Photos](#13-use-beautiful-photos)
    - [1.4 Keep Data Simple](#14-keep-data-simple)
    - [1.5 Repetition](#15-repetition)
  - [2. How to Read a Paper](#2-how-to-read-a-paper)
    - [2.1 Three-Pass Approach](#21-three-pass-approach)
      - [First Pass](#first-pass)
      - [Second Pass](#second-pass)
      - [Third Pass](#third-pass)
    - [2.2 Literature Survey](#22-literature-survey)
    - [2.3 Related Work](#23-related-work)
  - [3. Reading paper for Basic Path](#3-reading-paper-for-basic-path)
    - [3.1 First Pass](#31-first-pass)
    - [3.2 Second Pass](#32-second-pass)
      - [legacy 802.11](#legacy-80211)
      - [802.11E](#80211e)
      - [Evaluation](#evaluation)
      - [summary / conclusion](#summary--conclusion)


## 1. Five-minute presentation
*[Video](https://www.youtube.com/watch?v=YVgS_opYacQ): 5 Tips about Presentation Slides in 5 min by the Undergraduate Library at the University of North Carolina at Chapel Hill in 2017.*


### 1.1 Keep it simple
avoid using generic templates that people already know -> they will feel like they already know whats written there ?
avoid using to cluttered / distracting designs that draw the focus away from the actual contents to the design


### 1.2 Never Read From your Slides
Human brain isn't good at processing audio and text at the same time. Reading the text from the slides will likley lead to the audience to just read the text themselves and not listen to you.

Use as few words as possible
-> as much as necessary as little as possible

simple to read font
text big

Only put one point on a slide -> so the focus stays on the topic your currently covering and not on the next one already

(The section in this video is not very well structured and it feels like the title isn't suitable)


### 1.3 Use Beautiful Photos
photos can cause emotions
keep copyright law in mind 

(According to my understanding what kind of presentation also matters. Diffrent laws / fair use rights apply to for example a presentation in a classroom and a presentation for commercial purposes that gets braodcasted)

images should be big and have a high enough resolution to not appear low quality are badly readable

consider rule of thirds (focal point should be at 1/3 or 2/3 of the width / height)


### 1.4 Keep Data Simple
avoid to complex graphs that are hard to read

use / create graphs that focus on the important points you want to bring across and make them easily readable



### 1.5 Repetition
keep design consistent 

avoid using multiple fonts or color palettes

keep a simple color palette (2-3 colors)

use consistent layouts




## 2. How to Read a Paper
*[Document](https://web.stanford.edu/class/ee384m/Handouts/HowtoReadPaper.pdf) by S. S. Keshav and David R. Cheriton School of Computer Science, University of Waterloo (ON, Canada)*


### 2.1 Three-Pass Approach
Reading the paper in multiple passes, each of which focusing on more detail and building upon itself, avoids having to force yourself to reread the whole paper multiple times from start to finish.

#### First Pass
*get a general idea about the paper*

Read the following
1. title, abstract, introduction
2. section and sub-sections headings (only)
3. conclusion
4. check refrences (check-off ones already read)

evaluate if paper is worth reading for me with *five Cs*
1. *Category*: What type of paper is this?  
(measurement paper, analysis of an existing system, description of a research prototype)
2. *Context*: Which other papers is it related to?  
Which theoretical bases were used to analyze the problem?
3. *Correctness*: Do the assumptions appear to be valid?
4. *Contributions*: What are the paper’s main contributions?
5. *Clarity*: Is the paper well written?

Paper should be structered so that reviewers and readers can get the gist of it in 5 minutes.



#### Second Pass
*understand papers content (no details yet)*

read paper but ignore technical details like proofs  
writing down comments/key points helps

look carefully at
1. figures, diagrams, illustrations  
axis properly labeled? error bars included? statistical significancec?
2. mark relevant unread refrences for further reading

Second pass can take up to one hour.  
Afterwards able to summarize the papers contents with supporting evidence  

Second Pass is good enough for a paper I'm interested in but not part of my research

If unable to understand the paper (for wathever reason):
- set paper aside and hope it's not relevant for my future career
- read again (other time / after more research)
- go to third pass



#### Third Pass
*understand paper in depth with details*

try and *virtually re-implementent* the paper, based upon the same assumptions as the author used

identify and challenge every assumption in every statement

compare how I would present an idea with how it's done in the paper

can take up to 4-5 hours for beginner and 1 hour for experienced reader

should be able to reconstruct the entire structure of paper from memory as well as identify weak and strong points


### 2.2 Literature Survey
Reading papers in fiel I'm not familiar in to get an understanding of the topic

1. Use academic search engine (Google Scholar, CiteSeer, ...) with keywords
   - do first pass for papers
   - read related work section  
  if a recent survey paper exist -> done (lucky)
2. identify shared citations / author names  
  -> indicates the key authors and paper in the field
   - through that find major confrences in the field 
3. check website of top confrences to find recent high-quality work
   - do second pass thorugh those papers and the ones to be key earlier
     - if papers often cite a not yet identified paper, read that one as well

### 2.3 Related Work
*for reviewers*: Timothy Roscoe’s paper on [“Writing reviews for systems conferences”](https://people.inf.ethz.ch/troscoe/pubs/review-writing.pdf)

*wiriting techical papers*: Henning Schulzrinne’s [website](https://www.cs.columbia.edu/~hgs/etc/writing-style.html)  
George Whitesides’s [overview](https://intra.ece.ucr.edu/~rlake/Whitesides_writing_res_paper.pdf) of the process

*general research skills*: Simon Peyton Jones [website](https://simon.peytonjones.org/research-skills/)






## 3. Reading paper for Basic Path
*applying the Three-Pass Approach to understand the [Analysis of IEEE 802.11e for QoS support in wireless LANs](https://ieeexplore.ieee.org/document/126585) paper* 


### 3.1 First Pass

Answering the *five Cs*

1. *Category*: What type of paper is this?  
(measurement paper, analysis of an existing system, description of a research prototype,...)

It's protocol analysis and simulation-based evaluation paper.


2. *Context*: Which other papers is it related to?  

Which theoretical bases were used to analyze the problem?
It analyzes the at the time proposed IEEE 802.11e standard and compares it with the predecessor IEEE 802.11 standard focusing on QoS


3. *Correctness*: Do the assumptions appear to be valid?

I found basicaly no assumptions, or at least I didn't manage to notice them.
The paper seems to be based upon a solid basis (the standards by IEEE).

4. *Contributions*: What are the paper’s main contributions?

It compares a then draft of a new standard with the *legacy* version in terms of QoS, providing an analysis based upon simulations to evaluate the effectifness of the new protcol.

5. *Clarity*: Is the paper well written?

The structure seems coherent and logical. Just by skimming the article I got a general idea what the paper wants to show.

*Conclusion*: Based upon the first pass I believe this paper is worth reading, in order to understand the 802.11e standard (altough I would've had to read the paper anyways because of the Course)


### 3.2 Second Pass
*short summary of the main points in the paper, based upon my understanding of the material*

#### legacy 802.11

legacy 802.11 uses a CSMA/CA concept

To enable QoS Support it uses Point Coordination Function (PCF), which allows for time-bound QoS services centrally controled by the point Coordinator (CP; often the AP).

This implementation has it's limitations. It uses a Target beacon transmission time (TBTT) to sync the timers of the stations and tramsit protocol deliverd information (through beacon frames).  
But because the CP needs to wait for the channel to be idle and a PIFS (shorter wait time than a normal transmission, i.e. DIFS -> DIFS > PIFS), delays between the actual time and the TBTT can occur. This then may lead to the QoS to be affected.

Besides that the transmision time for polled stations (by PCF) isn't known and therefore out of the control of the CP, which may affect QoS for other stations.

#### 802.11E

hybrid coordination funciton (HCF) 
- contention-based channel acess (enhanced distributed channel access - EDCA)
- controlled channel access (HCF controlled channel access - HCCA)

differentiate between CP and CFP (Contention Phase and Contention Free Phase) as in legacy 802.11

**Imporvements over legacy 802.11**

- backoff entity must not utilize radio ressources for a duration longer than a specified limit (transmission opportunity - TXOP)
  - during CP -> EDCA-TXOPS  
    limited by QBSS wide paramter *TXOP-limit*
  - during CFP -> HCCA-TXOP
- no backoff entity transmits across TBTT -> better control for HC
- backoff entity can transmit to another backoff entity without communcating with AP (Direct link protocl - DLP)


**HCF contention-based medium access**

QoS support in EDCA

access categories (AC) -> prioritization through AC-specific contention paramters
1. AC_VO (voice)
2. AC_VI (video)
3. AC_BE (best effort)
4. AC_BK (background)
paramteres for ACs are defined by HC 

each entity start countint don the backoff-counter, after medium is idle by the Arbitration interfrae space (AIFS[AC]; AIFS[AC]$\geq$DIFS)
can be increased by arbitration interfram space number (AIFSN[AC])

$AIFS[AC] = SIFS + AIFSN[AC] \cdot aSlotTime, \;\; AIFSN[AC]\geq2$

AIFS[AC] should be equal to DIFS

Contention Window is dependent on AC (CWmin[AC])


QoS Support in HCCA

only HC can sen CF-Poll or transmit Downlink Data
only HC can allocate TXOPs


**Improved Efficiency**
Block acknowledgment: allows multiple MPUDUs to be transmitted with only one ACK
Direct Link Protocol (DLP): backoff entitiies can communication in a QBSS directlyo

#### Evaluation


event-driven stochastic model

 thorughpout in an isolated QBSS with four stations
-> shows that the priority system works, i.e. the data with higher priority retains the throughpout 


avialabe edca throughpout with increasing number of stations

Qos for edcas mdium access in isolated qbss
throughput is reduced more quickly and also in the AC_VO, because of lower CW_min and CW_ma


QoS guarantess with prioriized access of HC
HCCA delays stay more consistent and lower than EDCS



#### summary / conclusion
overlapping QBSS problem reaims to be resolved?







