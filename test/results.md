# Honest test: model vs our own labels

We labelled **50** randomly chosen posts ourselves before looking at the model's answers.

| | Agrees with us | Count |
|---|---|---|
| Transformer (`cardiffnlp/twitter-roberta-base-sentiment-latest`) | **66%** | 33 / 50 |
| Word-list baseline (VADER) | **40%** | 20 / 50 |

## Where the transformer goes wrong

| our label ↓ / predicted →   |   negative |   neutral |   positive |
|:----------------------------|-----------:|----------:|-----------:|
| negative                    |         19 |         7 |          0 |
| neutral                     |          6 |        10 |          2 |
| positive                    |          1 |         1 |          4 |

## Where the word-list baseline goes wrong

| our label ↓ / predicted →   |   negative |   neutral |   positive |
|:----------------------------|-----------:|----------:|-----------:|
| negative                    |          9 |         8 |          9 |
| neutral                     |          3 |         8 |          7 |
| positive                    |          2 |         1 |          3 |

Both wrong on the same post: 14. Baseline right where the transformer was wrong: 3.

## Every post the transformer got wrong

The brief asks for at least three failures with an explanation. We explain the most instructive ones below (also in the README, under "Failures that taught us the most"); the other rows are listed for completeness.

| Post | Us | Transformer (confidence) | VADER | Why it went wrong (fill in) |
|---|---|---|---|---|
| I don’t know how it works there, but Starlink was one of my choices when I moved here and it’s so tempting because the price is so low. I didn’t wanna be beholding to him so I didn’t get it, but I probably would’ve saved money if I had. | neutral | positive (42%) | neutral | |
| I would love to know @user how susceptible we are in the Hunter Valley as we have to use Starlink as Telstra can’t provide connection. Is Australia vulnerable? #auspol | negative | neutral (66%) | positive | |
| EE has been down nearly 2 hours now, and they report that it's scheduled outage, where was the notice for this? Nowhere. Anyway, they're apparently upgrading the mast here, and rumoured to be connecting with StarLink for situations like this so they connect customers to that while they work 🤷🏼‍♂️ | neutral | negative (75%) | positive | |
| I live in cottage country and internet here is piss poor. There are 10 cottages in here and 9 of them have starlink attached to their roof. Guess which roof doesn't have starlink. | neutral | negative (87%) | negative | Joke with a rude word: the model reacted to "piss poor", but the writer is making a wry joke, not complaining about Starlink. |
| I'm not sure, but my Starlink will be disconnected and returned by the end of the week. I may not have much control, but what is within my domain to influence will be done. He won't get a penny more of my money! Especially when it seems he prefers Kopecks anyway... | neutral | negative (62%) | negative | |
| Time for all former US alies to move away from US internet infrastructures, starting with Starlink. | negative | neutral (59%) | neutral | Negativity without negative words: a call to boycott, but no single word is negative, so both methods missed it. |
| 🌍 Technology and geopolitics are becoming increasingly connected. 🚀 This latest Starlink development raises important questions. More in my bio. | neutral | positive (61%) | positive | |
| Agreed, it's not just Starlink. Much of the legislation governing the internet was developed when Ted Stevens ran the Senate committee. He announced that the internet was "A series of tubes." Yes, really, that was the level of sophistication applied. Silicon Valley dictated the terms of governance. | negative | neutral (72%) | positive | |
| Alternative? Eutelsat I see Starlink ads everywhere online, sometimes twice in the same NYT article. | negative | neutral (78%) | neutral | |
| Rural/remote dependency on Starlink due to lack of / intermittent service from SaskTel - running equipment, computers, and machines that rely on an internet connection, think GPS for seeding, spraying - payroll, banking, data collection & reporting. Some people are still on dial up speeds. | neutral | negative (60%) | negative | |
| And to clear up any misconception the interceptors can go significantly slower than their target and still be effective, but there is a limit to that. The bandwidth restriction also puts limits on the range of Starlink integrated interceptors. | negative | neutral (56%) | positive | Not about the connection: military post ("interceptors") that slipped through our topic filter. |
| Are starlink speeds actually measured in km/h? That’s a pretty weird unit for measuring the speed of digital communications. kb/s or mb/s would make more sense. | neutral | negative (68%) | positive | A question that sounds negative: "weird" pushed the model to negative, but it is a genuine question. |
| "I think you could say that Starlink, in a way, it has a connected purpose, but it also has a purpose of surveillance, so, and it's also a collection purpose," Gibney said. "It's collecting data for his AI systems. | negative | neutral (85%) | neutral | |
| I'd chill a bit. Starlink isn't much of a dependency for any other Telstra service. In NSW, which I know best, most emergency services telecoms are terrestrial radio, with Starlink filling in hard-to-reach places. (I'm old enough to remember new homes waiting years to get phones...) | positive | neutral (65%) | positive | |
| moscow escalates mass strikes, while the US enriches putler with diesel purchases, throttles vital Starlink internet and appears to withhold life-saving intelligence 👉11 ways to donate to the Wild Hornets: linktr.ee/WildHornets $10 = 1 raffle ticket | neutral | negative (69%) | positive | Not about the connection: a war post that slipped through our topic filter ("putler", "moscow" were not on the off-topic list). |
| Yet a Canadian telco, Rogers, uses Starlink to expand their cell service coverage area. CORPORATE PIGS | positive | negative (62%) | positive | |
| Mykhailo Fedorov is the ex-Minister of Defense. One of his supporter's talking points is that he is friends with all the tech bros. Meidas is behind the curve on that update. The speed referred to is for the civilian version of Starlink which was always throttled at 160. | negative | neutral (76%) | positive | Not about the connection: Ukraine/military post that slipped through our topic filter. |