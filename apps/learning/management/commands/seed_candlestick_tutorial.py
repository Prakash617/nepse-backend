"""Management command to seed the complete 'Understanding Candlestick Charts' tutorial."""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.learning.models import (
    Tutorial,
    TutorialCategory,
    TutorialLesson,
    TutorialQuiz,
    TutorialQuizOption,
)


class Command(BaseCommand):
    help = "Seeds categories and the complete 17-lesson 'Understanding Candlestick Charts' tutorial."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding Tutorial Categories...")

        # 1. Categories
        tech_cat, _ = TutorialCategory.objects.update_or_create(
            slug="technical-analysis",
            defaults={
                "name": "Technical Analysis",
                "description": "Master price action, Japanese candlesticks, chart patterns, and technical indicators for NEPSE trading.",
                "icon": "TrendingUp",
                "display_order": 1,
                "is_active": True,
            },
        )

        fund_cat, _ = TutorialCategory.objects.update_or_create(
            slug="fundamental-analysis",
            defaults={
                "name": "Fundamental Analysis",
                "description": "Understand financial ratios, quarterly earnings reports, P/E, EPS, ROE, and intrinsic valuation of Nepali companies.",
                "icon": "FileText",
                "display_order": 2,
                "is_active": True,
            },
        )

        risk_cat, _ = TutorialCategory.objects.update_or_create(
            slug="risk-management",
            defaults={
                "name": "Risk Management & Psychology",
                "description": "Protect your capital through position sizing, stop losses, risk-reward ratios, and emotional discipline in trading.",
                "icon": "ShieldCheck",
                "display_order": 3,
                "is_active": True,
            },
        )

        adv_cat, _ = TutorialCategory.objects.update_or_create(
            slug="advanced-strategies",
            defaults={
                "name": "Advanced Trading Strategies",
                "description": "Multi-timeframe analysis, volume profile, sector rotation, and algorithmic screening for the Nepal Stock Exchange.",
                "icon": "Cpu",
                "display_order": 4,
                "is_active": True,
            },
        )

        self.stdout.write("Seeding Candlestick Tutorial...")

        # 2. Main Tutorial
        tutorial, _ = Tutorial.objects.update_or_create(
            slug="understanding-candlestick-charts",
            defaults={
                "category": tech_cat,
                "title": "Understanding Candlestick Charts",
                "short_description": "Learn how to read Japanese candlesticks from scratch. Master OHLC, single candle patterns, multi-candle reversal formations, and avoid common NEPSE trading traps.",
                "content": (
                    "Welcome to **Understanding Candlestick Charts**, the comprehensive guide for traders on the Nepal Stock Exchange (NEPSE).\n\n"
                    "Japanese candlestick charts are the bedrock of modern technical analysis. In this course, you will learn the mechanics behind price movement, discover high-probability reversal and continuation patterns, and learn how to apply them directly to NEPSE stocks.\n\n"
                    "### What You Will Learn:\n"
                    "- The four components of price: Open, High, Low, and Close (OHLC).\n"
                    "- How to interpret the psychological battle between buyers (bulls) and sellers (bears).\n"
                    "- Reversal patterns including Hammer, Bullish Engulfing, Morning Star, Shooting Star, and Evening Star.\n"
                    "- Indecision patterns such as Doji and Spinning Top.\n"
                    "- Practical NEPSE case studies with volume confirmation.\n"
                    "- Common mistakes beginners make when trading candle patterns in Kathmandu."
                ),
                "difficulty": Tutorial.DIFFICULTY_BEGINNER,
                "estimated_minutes": 45,
                "display_order": 1,
                "is_featured": True,
                "is_published": True,
            },
        )

        # 3. 17 Lessons
        lessons_data = [
            {
                "order": 1,
                "title": "Introduction to Candlestick Charts",
                "slug": "introduction-to-candlestick-charts",
                "estimated_minutes": 4,
                "content": """# Introduction to Candlestick Charts

Candlestick charts originated in 18th-century Japan, developed by rice trader **Munehisa Homma**. Homma realized that while the supply and demand of rice drove the market, the *emotions* of traders had a colossal influence on prices.

Decades later, in the late 1980s, an American analyst named Steve Nison introduced candlestick techniques to the Western financial world through his landmark book, *Japanese Candlestick Charting Techniques*.

---

### Why Candlesticks Matter on NEPSE

Before candlesticks, traders used plain line charts or bar charts. A traditional line chart merely connects the daily **Closing Price**. While simple, it hides critical intra-day drama:
- Did the stock spike dramatically during the 11:00 AM opening session?
- Did sellers aggressively push the stock down to circuit limits before buyers staged a miraculous afternoon recovery?

A candlestick reveals the entire emotional struggle of that trading day at a single glance.

```
       Line Chart                  Candlestick Chart
       Only shows Close            Shows Open, High, Low, & Close
             ●                     
            / \\                            │ (High)
           /   \\                       ┌───┴───┐
          /     ●                      │  BODY │
         ●                             └───┬───┘
                                           │ (Low)
```

### The Power of Visual Representation

Candlesticks make it instantly visible who controlled the session:
1. **Green (Bullish):** Buyers were in complete control; price closed higher than it opened.
2. **Red (Bearish):** Sellers dominated the session; price was driven down from opening highs.
3. **Wicks/Shadows:** Reveal price rejection and the outer limits of volatility reached during NEPSE trading hours (11:00 AM – 3:00 PM).

In the next lesson, we will dissect the four foundational data points of every candlestick: **OHLC**.
""",
                "quizzes": [
                    {
                        "question": "What key advantage does a candlestick chart have over a standard closing line chart on NEPSE?",
                        "explanation": "Candlestick charts provide Open, High, Low, and Close (OHLC) data, revealing intraday price battles and rejection wicks that line charts conceal.",
                        "options": [
                            {"text": "It displays Open, High, Low, and Close, showing intraday volatility and sentiment.", "is_correct": True, "explanation": "Correct! Candlesticks pack four price points into a single bar."},
                            {"text": "It guarantees that the next trading day will close in profit.", "is_correct": False, "explanation": "No chart can guarantee future profit."},
                            {"text": "It only shows the final transaction price at 3:00 PM.", "is_correct": False, "explanation": "That describes a basic line chart, not a candlestick."},
                            {"text": "It eliminates the need for brokers or TMS accounts.", "is_correct": False, "explanation": "Candlesticks are purely visual charting tools."},
                        ],
                    }
                ],
            },
            {
                "order": 2,
                "title": "Understanding OHLC",
                "slug": "understanding-ohlc",
                "estimated_minutes": 5,
                "content": """# Understanding OHLC: Open, High, Low, Close

Every single candlestick on NEPSE represents price activity over a specific timeframe (e.g., 5-minute, 1-hour, or 1-Day). Each candle is constructed using four fundamental numbers known as **OHLC**:

1. **Open (O):** The price at which the very first trade was matched when the session or timeframe started.
2. **High (H):** The absolute highest price matched during that timeframe.
3. **Low (L):** The absolute lowest price matched during that timeframe.
4. **Close (C):** The final price matched when the timeframe or session ended.

---

### Anatomy of an OHLC Candle

The distance between the **Open** and the **Close** forms the **Real Body**.
The thin lines extending above and below the body are called **Wicks** or **Shadows**.

```
         BULLISH CANDLE (Green)                   BEARISH CANDLE (Red)
         Close > Open                            Close < Open

             High                                    High
              │  (Upper Wick)                         │  (Upper Wick)
          ┌───┴───┐  ← Close                      ┌───┴───┐  ← Open
          │       │                               │       │
          │ BODY  │                               │ BODY  │
          │       │                               │       │
          └───┬───┘  ← Open                       └───┬───┘  ← Close
              │  (Lower Wick)                         │  (Lower Wick)
             Low                                     Low
```

### Realistic Simulated NEPSE Example: NABIL

Imagine watching **Nabil Bank (NABIL)** on a Sunday trading session:
- **11:00 AM Open:** First matched order at **NPR 520.00**.
- **12:30 PM High:** Institutional buying drives the price up to a peak of **NPR 545.00**.
- **01:45 PM Low:** Profit taking pushes the stock momentarily down to **NPR 515.00**.
- **03:00 PM Close:** Active bidding settles the day at **NPR 538.00**.

Because the Close (538.00) is **higher** than the Open (520.00), this forms a **Bullish Green Candle**:
- Upper wick: Extends from 538.00 up to 545.00 (7 rupees of upper rejection).
- Real body: NPR 520.00 to NPR 538.00 (18 rupees of net bullish gain).
- Lower wick: Extends from 520.00 down to 515.00 (5 rupees of dip before buying resumed).
""",
                "quizzes": [
                    {
                        "question": "If a stock opens at NPR 450, hits a high of NPR 480, drops to a low of NPR 440, and closes at NPR 470, what kind of candle is formed?",
                        "explanation": "Because the Close (470) is higher than the Open (450), it is a bullish candle with a real body spanning from 450 to 470.",
                        "options": [
                            {"text": "A bullish candle with real body between 450 and 470", "is_correct": True, "explanation": "Correct! Close > Open produces a bullish real body."},
                            {"text": "A bearish candle because the low was 440", "is_correct": False, "explanation": "The low forms the lower shadow, but body color depends on Open vs Close."},
                            {"text": "A Doji candle with no body", "is_correct": False, "explanation": "A Doji requires Open and Close to be virtually equal."},
                            {"text": "An inverted hammer with no lower wick", "is_correct": False, "explanation": "Here there is a 10 rupee lower wick (450 down to 440)."},
                        ],
                    }
                ],
            },
            {
                "order": 3,
                "title": "Bullish and Bearish Candles",
                "slug": "bullish-and-bearish-candles",
                "estimated_minutes": 5,
                "content": """# Bullish and Bearish Candles

In trading, sentiment is categorized into two opposing forces:
- **Bulls:** Traders who believe prices will rise and are actively buying.
- **Bears:** Traders who believe prices will fall and are selling or taking profits.

---

### The Bullish Candle (Green / White)

A candle is **bullish** when:
$$\\text{Close} > \\text{Open}$$

- **Meaning:** Buyers absorbed all selling pressure and forced the market higher by the end of the session.
- **Strongest Bullish Candle (Marubozu):** A long green body with virtually no upper or lower wicks. This indicates relentless buying from open to close.

```
       BULLISH MARUBOZU                 STANDARD BULLISH
        High = Close                         High
        ┌───────────┐                         │
        │           │                     ┌───┴───┐
        │   BUYERS  │                     │       │
        │  DOMINATE │                     │       │
        │           │                     └───┬───┘
        └───────────┘                         │
        Low = Open                           Low
```

---

### The Bearish Candle (Red / Black)

A candle is **bearish** when:
$$\\text{Close} < \\text{Open}$$

- **Meaning:** Sellers overwhelmed buyers throughout the session.
- **Bearish Marubozu:** Opens near its high and plunges straight down to close near its low with heavy sell volume on TMS.

```
       BEARISH MARUBOZU                 STANDARD BEARISH
        High = Open                          High
        ┌───────────┐                         │
        │           │                     ┌───┴───┐
        │  SELLERS  │                     │       │
        │  DOMINATE │                     │       │
        │           │                     └───┬───┘
        └───────────┘                         │
        Low = Close                          Low
```

### NEPSE Market Tip: Beware the 2:45 PM Shift

On NEPSE, the final 15 minutes of trading (2:45 PM to 3:00 PM) frequently see aggressive institutional order matching. Always wait for the official daily candle to close before confirming whether a candle is truly bullish or bearish.
""",
                "quizzes": [
                    {
                        "question": "What defines a Bullish Marubozu candle?",
                        "explanation": "A Bullish Marubozu has a long green body with virtually no wicks, showing buyers controlled the session from open to close.",
                        "options": [
                            {"text": "A long green candle with little to no wicks where Open=Low and High=Close", "is_correct": True, "explanation": "Correct! It shows decisive, uninterrupted buying conviction."},
                            {"text": "A tiny candle with very long upper and lower shadows", "is_correct": False, "explanation": "That describes a spinning top or high-wave candle."},
                            {"text": "A candle where the Close is lower than the Open", "is_correct": False, "explanation": "That is bearish by definition."},
                            {"text": "A candle that only occurs when NEPSE hits a circuit breaker", "is_correct": False, "explanation": "A Marubozu can occur on any normal trading session."},
                        ],
                    }
                ],
            },
            {
                "order": 4,
                "title": "Candle Body and Wicks",
                "slug": "candle-body-and-wicks",
                "estimated_minutes": 5,
                "content": """# Candle Body and Wicks: Decoding Price Rejection

While the candle **body** tells you the net result of the session, the **wicks** (also known as tails or shadows) tell you the *story of rejection*.

---

### What Does the Body Tell You?

1. **Large Body:** Represents strong conviction, high trading volume, and decisive directional momentum.
2. **Small Body:** Represents tight consolidation, lack of conviction, or equilibrium between buyers and sellers.

---

### What Do Wicks Tell You?

Wicks reveal price levels where one group tried to move the market, but the opposing group pushed back forcefully.

```
       LONG UPPER WICK (Bearish Rejection)       LONG LOWER WICK (Bullish Rejection)
                   High                                     High
                    │                                     ┌───┴───┐
                    │  ← Buyers tried to push             │ BODY  │
                    │    up here, but were                └───┬───┘
                    │    rejected by sellers!                 │  ← Sellers tried to dump
                ┌───┴───┐                                     │    shares here, but
                │ BODY  │                                     │    buyers stepped in!
                └───┬───┘                                     │
                   Low                                       Low
```

### Interpreting Lower Wicks at NEPSE Support Levels

Suppose a hydropower stock like **UPPER** has maintained strong support around **NPR 180.00**.
During an intraday panic, price plunges to **NPR 172.00**. However, value buyers aggressively absorb the sell orders, lifting the price back to close at **NPR 182.00**.

The resulting candle displays a **long lower shadow**. This tells seasoned technical traders:
> *"Sellers attempted a breakdown below 180, but found immense liquidity and buying demand. Support held firmly."*
""",
                "quizzes": [
                    {
                        "question": "What is the primary psychological signal behind a long upper wick on a daily candle?",
                        "explanation": "A long upper wick indicates that buyers attempted to push prices higher, but strong selling pressure emerged to reject the higher price levels.",
                        "options": [
                            {"text": "Buyers were rejected at higher levels as sellers exerted heavy pressure", "is_correct": True, "explanation": "Spot on. The long upper wick marks rejection of higher prices."},
                            {"text": "Buyers completely overwhelmed sellers and closed at highs", "is_correct": False, "explanation": "If buyers closed at highs, there would be no upper wick."},
                            {"text": "The company declared an immediate bonus dividend", "is_correct": False, "explanation": "Candlestick wicks reflect market order flow, not announcements."},
                            {"text": "Trading was suspended for the remainder of the week", "is_correct": False, "explanation": "Upper wicks happen routinely in normal active markets."},
                        ],
                    }
                ],
            },
            {
                "order": 5,
                "title": "Hammer",
                "slug": "hammer",
                "estimated_minutes": 5,
                "content": """# The Hammer Pattern

The **Hammer** is one of the most reliable single-candlestick bullish reversal patterns in technical analysis. It typically appears at the bottom of a downtrend.

---

### Identification Rules

1. **Location:** Must appear after a sustained downtrend or after a sharp multi-day decline.
2. **Body:** A small real body at the upper end of the trading range (can be green or red, but green is stronger).
3. **Lower Wick:** Must be at least **two times** the length of the real body.
4. **Upper Wick:** Little to no upper wick (or negligible).

```
               HAMMER FORMATION
                    High
                  ┌───────┐
                  │ Body  │  ← Small real body at the top
                  └───┬───┘
                      │
                      │
                      │      ← Lower shadow at least 2x the body height
                      │        (Shows buyers rejecting lower prices)
                      │
                     Low
```

### Market Psychology Behind the Hammer

- The market opens and bears continue the prevailing downtrend, dumping shares aggressively.
- At the lows, buyers step in, recognizing undervaluation or key technical support.
- Buyers drive prices all the way back up to close near the day's open.
- The long tail signals that the bears have exhausted their supply, and bulls are seizing momentum.

### NEPSE Trading Rule: Confirmation is Mandatory

Never buy solely on a Hammer! In the Nepal market, wait for the **next candle** to confirm by closing above the Hammer's real body, ideally accompanied by an expansion in NEPSE turnover.
""",
                "quizzes": [
                    {
                        "question": "Which of the following is a mandatory criterion for a valid Hammer pattern?",
                        "explanation": "A valid hammer requires a lower shadow at least twice the length of the body, located at the bottom of a downtrend.",
                        "options": [
                            {"text": "The lower shadow must be at least twice the height of the real body", "is_correct": True, "explanation": "Correct! That dramatic lower rejection defines the hammer shape."},
                            {"text": "The upper wick must be three times longer than the lower wick", "is_correct": False, "explanation": "A hammer has little to no upper wick."},
                            {"text": "It must appear after a prolonged 50% uptrend", "is_correct": False, "explanation": "At the top of an uptrend, that shape is called a Hanging Man, not a Hammer."},
                            {"text": "The candle must be strictly black or red", "is_correct": False, "explanation": "A hammer can be green or red (green is even more bullish)."},
                        ],
                    }
                ],
            },
            {
                "order": 6,
                "title": "Inverted Hammer",
                "slug": "inverted-hammer",
                "estimated_minutes": 5,
                "content": """# The Inverted Hammer Pattern

The **Inverted Hammer** is another bullish reversal candlestick pattern that appears at the bottom of a downtrend. Visually, it looks like an upside-down hammer.

---

### Identification Rules

1. **Location:** Bottom of a downtrend or after a pullback to a support level.
2. **Body:** Small real body situated near the lower end of the daily price range.
3. **Upper Wick:** Long upper shadow that is at least **two times** the length of the body.
4. **Lower Wick:** Very small or non-existent lower shadow.

```
           INVERTED HAMMER
                High
                 │
                 │
                 │      ← Upper shadow at least 2x body height
                 │        (Bulls tested higher prices)
                 │
             ┌───┴───┐
             │ Body  │  ← Small body at the bottom
             └───────┘
                Low
```

### Psychological Shift

Why is a candle with an upper wick bullish when it appears at the bottom of a downtrend?
- In a downtrend, bears previously dominated every session without challenge.
- On the Inverted Hammer day, bulls mounted their first significant counter-offensive, driving prices up sharply.
- Even though bears pushed the price back toward the open before the 3:00 PM close, the fact that bulls tested those highs proves that aggressive accumulation has commenced.

### Confirmation Requirement

Because bears were able to force the price down from the highs before close, **confirmation on day two is essential**. Look for a gap up or a strong green candle closing above the Inverted Hammer's body on higher NEPSE volume.
""",
                "quizzes": [
                    {
                        "question": "Where does a valid Inverted Hammer pattern occur in market structure?",
                        "explanation": "An Inverted Hammer occurs at the bottom of a downtrend and signals a potential bullish reversal when confirmed.",
                        "options": [
                            {"text": "At the bottom of a downtrend or after a decline", "is_correct": True, "explanation": "Correct. At the top of an uptrend, this exact shape is called a Shooting Star."},
                            {"text": "At the peak of an all-time high", "is_correct": False, "explanation": "At the peak, it is a bearish Shooting Star."},
                            {"text": "Only during sideways consolidation with zero turnover", "is_correct": False, "explanation": "Reversal candles require an established prior trend to reverse."},
                            {"text": "On Sunday pre-market opening only", "is_correct": False, "explanation": "It forms across any complete candlestick timeframe."},
                        ],
                    }
                ],
            },
            {
                "order": 7,
                "title": "Bullish Engulfing",
                "slug": "bullish-engulfing",
                "estimated_minutes": 5,
                "content": """# Bullish Engulfing: Two-Candle Reversal

The **Bullish Engulfing** pattern is one of the highest-conviction two-candlestick reversal signals in technical analysis.

---

### Pattern Structure

It consists of two consecutive candles:
1. **Day 1 (Bearish):** A small red candle in line with the current downtrend.
2. **Day 2 (Bullish):** A large green candle that opens lower than (or equal to) Day 1's close, and rallies vigorously to close **above** Day 1's open.

The real body of Day 2 completely **engulfs** the real body of Day 1!

```
       BULLISH ENGULFING PATTERN

       Day 1           Day 2
       (Red)          (Green)
                     ┌─────────┐  ← Closes well ABOVE Day 1 open
                     │         │
          ┌─────┐    │         │
          │ Red │    │  Green  │  ← Green body completely engulfs
          │Body │    │  Body   │    the preceding red body!
          └─────┘    │         │
                     │         │
                     └─────────┘  ← Opens AT or BELOW Day 1 close
```

### Real NEPSE Case Study: Commercial Bank Reversal

Consider **NICA** after a multi-week drop from NPR 800 down to NPR 450:
- **Sunday:** NICA closes down at NPR 445 with a small red body.
- **Monday:** The stock opens flat at NPR 444, but mutual funds and retail buyers launch massive buy orders. By 3:00 PM, NICA rallies to close at NPR 465.
- The Monday green body (444 to 465) completely swallows Sunday's red body (445 to 452).

This shows an immediate, overwhelming transfer of power from sellers to buyers.
""",
                "quizzes": [
                    {
                        "question": "What must the second candle in a Bullish Engulfing pattern do?",
                        "explanation": "The second green candle's body must completely cover/engulf the body of the previous red candle.",
                        "options": [
                            {"text": "Its green real body must completely engulf the real body of the prior red candle", "is_correct": True, "explanation": "Correct! That visual engulfment reflects overwhelming buyer dominance."},
                            {"text": "It must be half the size of the previous candle", "is_correct": False, "explanation": "A smaller candle inside a larger one is a Harami, not an Engulfing pattern."},
                            {"text": "It must close lower than Day 1's low", "is_correct": False, "explanation": "That would be a bearish continuation."},
                            {"text": "It must be a Doji with identical Open and Close", "is_correct": False, "explanation": "An engulfing candle needs a robust, tall body."},
                        ],
                    }
                ],
            },
            {
                "order": 8,
                "title": "Morning Star",
                "slug": "morning-star",
                "estimated_minutes": 5,
                "content": """# The Morning Star: Three-Candle Bullish Pattern

Just as the morning star heralds the sunrise, the **Morning Star** candlestick pattern heralds a new bullish dawn following a dark downtrend.

---

### Structure: A Three-Day Story

1. **Day 1 (Bearish):** A tall, strong red candle that confirms bears are firmly in control.
2. **Day 2 (The Star):** A small-bodied candle (red, green, or Doji) that gaps down or trades at the bottom. This reflects indecision and bear exhaustion.
3. **Day 3 (Bullish):** A substantial green candle that closes at least **halfway (50%) or more** into the body of Day 1.

```
               THE MORNING STAR
          Day 1                        Day 3
         (Tall Red)                  (Tall Green)
         ┌─────────┐                 ┌─────────┐
         │         │                 │         │
         │  BEAR   │     50% line    │  BULL   │  ← Closes well past 50%
         ├ - - - - ┼ - - - - - - - - ┼ - - - - ┤    of Day 1 red body
         │         │                 │         │
         └─────────┘    Day 2        └─────────┘
                       (Star)
                       ┌─────┐
                       └─────┘
```

### Psychological Breakdown

- **Day 1:** Bears celebrate as prices tumble.
- **Day 2:** Bears fail to push prices lower despite negative sentiment. Volatility contracts.
- **Day 3:** Bulls take over completely, reclaiming previous losses and trapping late short-sellers or panic sellers.

When accompanied by expanding turnover on NEPSE, the Morning Star is among the highest-probability bottom reversal patterns available.
""",
                "quizzes": [
                    {
                        "question": "How far into Day 1's red body must Day 3 close for a classic Morning Star formation?",
                        "explanation": "In a classic Morning Star, the Day 3 green candle should close at least 50% (halfway) into Day 1's red body to confirm bullish strength.",
                        "options": [
                            {"text": "At least 50% (halfway) or higher into Day 1's red candle body", "is_correct": True, "explanation": "Correct! Closing deep into the first day's body proves buyer conviction."},
                            {"text": "Below Day 2's low", "is_correct": False, "explanation": "That would signify a bearish continuation, not a reversal."},
                            {"text": "Exactly 1 rupee below the open of Day 2", "is_correct": False, "explanation": "Day 3 must be a strong upward close."},
                            {"text": "The close must be identical to the low", "is_correct": False, "explanation": "A strong Day 3 closes near its high."},
                        ],
                    }
                ],
            },
            {
                "order": 9,
                "title": "Shooting Star",
                "slug": "shooting-star",
                "estimated_minutes": 5,
                "content": """# The Shooting Star: Top Bearish Reversal

The **Shooting Star** is the bearish mirror image of the Inverted Hammer. It appears at the peak of an uptrend and signals that the rally has run out of steam.

---

### Key Characteristics

1. **Location:** Appears at the top of an uptrend or near significant resistance.
2. **Body:** A small real body at the lower boundary of the day's price range.
3. **Upper Wick:** A very long upper shadow, at least **two times** the height of the real body.
4. **Lower Wick:** Little to no lower shadow.

```
               SHOOTING STAR
                    High
                     │
                     │
                     │   ← Long upper wick (at least 2x body)
                     │     Shows bulls failed to sustain highs
                     │
                 ┌───┴───┐
                 │ Body  │  ← Small body near the lows
                 └───────┘
                    Low
```

### The Story on NEPSE: The Retail Trap

Imagine a speculative stock like **SHIVM** has rallied 40% over two weeks.
- On Sunday morning, retail traders chase the breakout, pushing the stock up another +8% to **NPR 650.00**.
- Smart money and promoters use the surge in liquidity to unload their positions.
- By 2:30 PM, selling accelerates. By 3:00 PM, the stock closes back down at **NPR 605.00** (barely above open).
- The result is a tall upper wick at NPR 650 and a small body near NPR 605: a **Shooting Star**.

All buyers who purchased at NPR 630–650 are now trapped at a loss.
""",
                "quizzes": [
                    {
                        "question": "What does a Shooting Star pattern at an all-time high warn traders about?",
                        "explanation": "A Shooting Star warns that buyers were rejected at higher levels and profit taking/selling has taken control, indicating a potential bearish reversal.",
                        "options": [
                            {"text": "Bulls failed to hold higher levels and heavy distribution took place", "is_correct": True, "explanation": "Correct. The long upper tail shows rejection of highs."},
                            {"text": "The stock is guaranteed to gap up 10% tomorrow", "is_correct": False, "explanation": "A shooting star is a warning of downward reversal."},
                            {"text": "Bears have completely given up", "is_correct": False, "explanation": "Sellers were the ones who knocked the price down from the highs."},
                            {"text": "It indicates a long-term buy-and-hold signal", "is_correct": False, "explanation": "It warns traders to tighten stops or take profits."},
                        ],
                    }
                ],
            },
            {
                "order": 10,
                "title": "Hanging Man",
                "slug": "hanging-man",
                "estimated_minutes": 5,
                "content": """# The Hanging Man Pattern

The **Hanging Man** shares the exact visual appearance of a Hammer, but with one critical distinction: **it appears at the top of an uptrend**.

---

### Identification Criteria

1. **Prior Trend:** Established uptrend.
2. **Body:** Small real body at the upper end of the trading range.
3. **Lower Wick:** Long lower shadow, at least **twice** the length of the real body.
4. **Upper Wick:** Very small or absent.

```
       HAMMER vs HANGING MAN

       In a Downtrend = HAMMER            In an Uptrend = HANGING MAN
       (Bullish Reversal)                 (Bearish Warning)

             │                                  ▲
             ▼   ┌───┐                          │   ┌───┐
                 │   │                              │   │
                 └───┬───┘                          └───┬───┘
                     │                                  │
                     │                                  │
                     │                                  │
```

### Why is this Bearish?

If the market was able to recover and close near the highs, why is it called a "Hanging Man"?
- Because during the session, sellers were capable of driving the price down significantly (creating the long lower shadow).
- In a healthy uptrend, sellers should not have the power to create a deep drop.
- The sudden vulnerability reveals that buyers are losing their grip on supply.

### NEPSE Rule: Never Sell Without Confirmation

A Hanging Man requires confirmation on the subsequent trading session: the next candle must close **below** the Hanging Man's body.
""",
                "quizzes": [
                    {
                        "question": "What is the key visual difference between a Hammer and a Hanging Man?",
                        "explanation": "Visually, their shapes are identical. The difference is their context: a Hammer forms after a downtrend, while a Hanging Man forms after an uptrend.",
                        "options": [
                            {"text": "There is no visual difference; the difference is their position in the trend", "is_correct": True, "explanation": "Exactly right! Location within the trend determines the pattern."},
                            {"text": "The Hanging Man has no lower wick", "is_correct": False, "explanation": "Both have long lower wicks."},
                            {"text": "The Hammer only appears on quarterly earnings days", "is_correct": False, "explanation": "Both can form on any trading day."},
                            {"text": "A Hanging Man must always be green", "is_correct": False, "explanation": "A Hanging Man can be red or green (red is even more bearish)."},
                        ],
                    }
                ],
            },
            {
                "order": 11,
                "title": "Bearish Engulfing",
                "slug": "bearish-engulfing",
                "estimated_minutes": 5,
                "content": """# Bearish Engulfing: Two-Candle Top Reversal

The **Bearish Engulfing** pattern is a lethal top reversal pattern that signals institutional selling on NEPSE.

---

### Pattern Anatomy

1. **Day 1 (Bullish):** A small green candle continuing the uptrend.
2. **Day 2 (Bearish):** A large red candle that opens above (or equal to) Day 1's close, but drops precipitously to close **below** Day 1's open.

The red body completely engulfs the preceding green body.

```
       BEARISH ENGULFING PATTERN

       Day 1           Day 2
       (Green)         (Red)
                     ┌─────────┐  ← Opens AT or ABOVE Day 1 close
                     │         │
          ┌─────┐    │         │
          │Green│    │   Red   │  ← Red body completely engulfs
          │Body │    │  Body   │    the preceding green body!
          └─────┘    │         │
                     │         │
                     └─────────┘  ← Closes well BELOW Day 1 open
```

### Institutional Dumping at Resistance

When a sector on NEPSE (such as Microfinance or Banking) approaches major psychological resistance:
- Day 1 shows slowing momentum.
- Day 2 sees sellers dump large blocks of shares into the order book.
- By closing below Day 1's open, every trader who bought yesterday is plunged into a losing position, prompting further margin and panic sales.
""",
                "quizzes": [
                    {
                        "question": "In a Bearish Engulfing pattern, which body engulfs which?",
                        "explanation": "The second (red) candle's body must completely engulf the first (green) candle's body.",
                        "options": [
                            {"text": "The Day 2 red body engulfs the Day 1 green body", "is_correct": True, "explanation": "Correct! This signals sellers have overwhelmed the bulls."},
                            {"text": "The Day 1 green body engulfs the Day 2 red body", "is_correct": False, "explanation": "That would be a Harami pattern."},
                            {"text": "Both wicks must touch each other", "is_correct": False, "explanation": "Engulfing applies primarily to the real bodies."},
                            {"text": "Day 2 must close at zero", "is_correct": False, "explanation": "Prices cannot close at zero."},
                        ],
                    }
                ],
            },
            {
                "order": 12,
                "title": "Evening Star",
                "slug": "evening-star",
                "estimated_minutes": 5,
                "content": """# The Evening Star: Three-Candle Bearish Reversal

The **Evening Star** is the bearish counterpart of the Morning Star. Just as the evening star signals oncoming darkness, this pattern indicates an impending price decline.

---

### Three-Candle Blueprint

1. **Day 1 (Bullish):** A tall, strong green candle reflecting confident buying in the uptrend.
2. **Day 2 (The Star):** A small-bodied candle (red or green) showing indecision at the top. Buyers struggle to make progress.
3. **Day 3 (Bearish):** A tall red candle that closes **at least 50% or deeper** into the body of Day 1.

```
               THE EVENING STAR
                       Day 2
                       (Star)
                       ┌─────┐
                       └─────┘
          Day 1                        Day 3
        (Tall Green)                 (Tall Red)
         ┌─────────┐                 ┌─────────┐
         │         │                 │         │
         │  BULL   │     50% line    │  BEAR   │  ← Closes well below 50%
         ├ - - - - ┼ - - - - - - - - ┼ - - - - ┤    of Day 1 green body
         │         │                 │         │
         └─────────┘                 └─────────┘
```

### Risk Management Action

When an Evening Star is confirmed on NEPSE with high turnover, prudent traders take defensive action:
- Protect accrued profits by selling partial or full positions.
- Trail stop-losses tightly above the high of the Day 2 star.
""",
                "quizzes": [
                    {
                        "question": "What does Day 2 in an Evening Star formation signify?",
                        "explanation": "The small real body on Day 2 indicates buyer hesitation, momentum deceleration, and equilibrium between buyers and sellers before the drop.",
                        "options": [
                            {"text": "Deceleration of upward momentum and indecision at the highs", "is_correct": True, "explanation": "Correct. Day 2 marks the exhaustion of the rally."},
                            {"text": "An aggressive continuation of the bull run", "is_correct": False, "explanation": "If it were continuing aggressively, Day 2 would be a large green candle."},
                            {"text": "Immediate suspension of TMS trading", "is_correct": False, "explanation": "It is a standard price formation."},
                            {"text": "That sellers have completely disappeared from the market", "is_correct": False, "explanation": "Sellers are actively meeting buyers, stalling the advance."},
                        ],
                    }
                ],
            },
            {
                "order": 13,
                "title": "Doji",
                "slug": "doji",
                "estimated_minutes": 4,
                "content": """# The Doji: Pure Indecision

A **Doji** is formed when a stock's **Open and Close prices are virtually identical**. It represents absolute balance and indecision between buyers and sellers.

---

### Doji Varieties

```
    STANDARD DOJI       LONG-LEGGED DOJI       DRAGONFLY DOJI       GRAVESTONE DOJI
         │                    │                     │                      │
         │                    │                     │                      │
       ──┼──                ──┼──                 ──┴──                    │
         │                    │                     │                    ──┴──
         │                    │                     │
```

1. **Standard Doji:** Small upper and lower wicks; open and close meet in the center.
2. **Long-Legged Doji (Rickshaw Man):** Tremendous volatility occurred intraday, but neither party could hold ground.
3. **Dragonfly Doji:** Long lower shadow with open and close at the high. Bullish if found at support!
4. **Gravestone Doji:** Long upper shadow with open and close at the low. Bearish if found at resistance!

---

### The Golden Rule of Dojis

A Doji in isolation is **neither bullish nor bearish**. It is a **yellow traffic light** advising you:
> *"Slow down. The prevailing trend is pausing. A transition of power is underway."*

Always await the next candle's direction for confirmation.
""",
                "quizzes": [
                    {
                        "question": "What is the defining technical feature of any Doji candle?",
                        "explanation": "A Doji is characterized by Open and Close prices that are essentially equal, resulting in a horizontal line instead of a real body.",
                        "options": [
                            {"text": "The Open and Close are virtually equal, resulting in no real body", "is_correct": True, "explanation": "Correct! That cross-like shape reflects exact equilibrium."},
                            {"text": "It must have a massive green body", "is_correct": False, "explanation": "A Doji has no body."},
                            {"text": "It only occurs once a year on the Nepal Stock Exchange", "is_correct": False, "explanation": "Dojis occur frequently on daily and hourly charts."},
                            {"text": "It guarantees an instant trend continuation", "is_correct": False, "explanation": "Dojis indicate indecision and potential reversal."},
                        ],
                    }
                ],
            },
            {
                "order": 14,
                "title": "Spinning Top",
                "slug": "spinning-top",
                "estimated_minutes": 4,
                "content": """# The Spinning Top

A **Spinning Top** is a candlestick with a small real body positioned symmetrically between long upper and lower shadows.

---

### Anatomy

```
                SPINNING TOP
                     High
                      │
                      │   ← Upper Wick
                      │
                  ┌───┴───┐
                  │ Body  │  ← Small real body in the middle
                  └───┬───┘
                      │
                      │   ← Lower Wick
                      │
                     Low
```

### Spinning Top vs. Doji

- **Doji:** Open and Close are identical (no body).
- **Spinning Top:** Has a small real body (can be green or red), but the wicks in both directions are noticeably longer than the body.

### What it Means in the Market

The Spinning Top indicates a fierce tug-of-war where neither the bulls nor the bears could gain the upper hand:
- Bulls pushed prices up to the high.
- Bears pushed prices down to the low.
- By the closing bell, price settled right back near the open.

When you spot a cluster of Spinning Tops on the NEPSE Index chart, it typically signifies sideways consolidation before a breakout.
""",
                "quizzes": [
                    {
                        "question": "How does a Spinning Top differ from a Doji?",
                        "explanation": "A Spinning Top has a small real body with upper and lower shadows, whereas a Doji has essentially no real body because Open equals Close.",
                        "options": [
                            {"text": "A Spinning Top has a small real body, whereas a Doji has virtually no body", "is_correct": True, "explanation": "Correct! Both indicate indecision, but the body thickness differs."},
                            {"text": "A Spinning Top never has an upper shadow", "is_correct": False, "explanation": "Spinning Tops have both upper and lower shadows."},
                            {"text": "A Doji is only found in crypto markets", "is_correct": False, "explanation": "Both patterns exist across all financial markets."},
                            {"text": "A Spinning Top always predicts a market crash", "is_correct": False, "explanation": "Spinning tops signify consolidation and neutrality."},
                        ],
                    }
                ],
            },
            {
                "order": 15,
                "title": "Practical NEPSE Examples",
                "slug": "practical-nepse-examples",
                "estimated_minutes": 6,
                "content": """# Practical NEPSE Examples

*Note: The following scenarios are realistic educational simulations based on real Nepal Stock Exchange price structures.*

---

### Case Study 1: The NABIL Hammer at 500 Support

- **Context:** Nabil Bank drops from NPR 620 to NPR 500 over 3 weeks.
- **Pattern:** At NPR 500, a Hammer forms with an open of 505, low of 488, and close of 508.
- **NEPSE Turnover:** Turnover surges to NPR 12 Crore on the reversal day.
- **Outcome:** The subsequent day opens at 512 and rallies to 530, validating the Hammer bottom.

```
      Price (NPR)
        600 │ ╲
        560 │  ╲ Downtrend
        520 │   ╲          ┌─┐
        500 │    ╲   ┬     │ │ Confirmation Green Candle
        480 │     └──┴─────┴─┘
                     ▲ Hammer
```

---

### Case Study 2: The Hydropower Shooting Star Trap

- **Context:** A fast-moving hydro stock climbs 35% in 6 trading days.
- **The Setup:** On Tuesday, the stock gaps up +6% to NPR 410. Retail traders enter fearing they will miss out (FOMO).
- **The Reversal:** Big operators dump over 150,000 shares into the frenzy. By 3:00 PM, the stock closes at NPR 372 (near the low of 370).
- **The Result:** A textbook Shooting Star with a massive 38-rupee upper wick. Over the following week, the stock tumbles back to NPR 330.

---

### Three NEPSE Golden Rules

1. **Volume Confirms Pattern:** A Hammer with low turnover is suspect; a Hammer with 3x average daily turnover is high-conviction.
2. **Context Over Shape:** A Hammer in the middle of a sideways consolidation is noise; at multi-month support, it is actionable.
3. **T+2 Settlement Awareness:** In Nepal's T+2 cycle, intraday traders cannot exit immediately. Always demand higher confirmation before taking swing entries.
""",
                "quizzes": [
                    {
                        "question": "Why is turnover/volume confirmation particularly crucial for candlestick reversals on NEPSE?",
                        "explanation": "High turnover indicates institutional sponsorship and authentic buying/selling power, filtering out low-volume retail false signals.",
                        "options": [
                            {"text": "High turnover proves institutional participation and validates that the price move is genuine", "is_correct": True, "explanation": "Correct! Volume confirms the conviction behind the candlestick."},
                            {"text": "Volume is irrelevant on the Nepal Stock Exchange", "is_correct": False, "explanation": "Volume is one of the most critical metrics on NEPSE."},
                            {"text": "Because NEPSE automatically cancels orders with low volume", "is_correct": False, "explanation": "Low volume trades still execute, but lack institutional weight."},
                            {"text": "High turnover reduces broker commission to 0%", "is_correct": False, "explanation": "Broker commissions are regulated and fixed by SEBON."},
                        ],
                    }
                ],
            },
            {
                "order": 16,
                "title": "Common Trading Mistakes",
                "slug": "common-trading-mistakes",
                "estimated_minutes": 5,
                "content": """# Common Trading Mistakes with Candlesticks

Even seasoned traders occasionally fall into psychological and technical traps. Here are the top mistakes to avoid when applying candlesticks to the Nepal market.

---

### 1. Trading Candles in Isolation
**The Mistake:** Buying every green Hammer or selling every Shooting Star without checking where it formed.
**The Fix:** Always evaluate **Support & Resistance**, **Moving Averages**, and the **NEPSE Index trend**. A Hammer is only meaningful if it tests a legitimate support floor.

---

### 2. Jumping the Gun Before Candle Close
**The Mistake:** Entering a trade at 1:30 PM because a candle "looks like a Hammer", only to watch sellers crush it into a giant red bar by 3:00 PM.
**The Fix:** Candlestick patterns are only valid once the candle has officially **closed**. Always wait for the 3:00 PM closing print or trade the next morning's confirmation.

---

### 3. Ignoring the Prevailing Macro Trend
**The Mistake:** Trying to pick bottoms on speculative micro-caps during a prolonged bear market.
**The Fix:** In a severe downtrend, bullish reversal patterns have a higher failure rate. Trade smaller position sizes or wait for structural trend changes (higher highs and higher lows).

---

### 4. Forgetting Risk-to-Reward (Stop Losses)
**The Mistake:** Entering a trade without a predefined exit point if the pattern fails.
**The Fix:** Always set your mental or system stop-loss just below the low of the reversal candle (e.g., 2–3% below a Hammer's lower shadow).
""",
                "quizzes": [
                    {
                        "question": "What is the danger of executing a trade based on a candlestick before the market session closes at 3:00 PM?",
                        "explanation": "Intraday price action can fluctuate wildly; an apparent Hammer at 1:30 PM can turn into a Bearish Marubozu by 3:00 PM if late selling hits.",
                        "options": [
                            {"text": "The candle is incomplete and late-session volatility can completely change its shape", "is_correct": True, "explanation": "Exactly right. Only a closed candle reflects the final verdict."},
                            {"text": "NEPSE does not allow trades between 1:00 PM and 3:00 PM", "is_correct": False, "explanation": "NEPSE trades continuously from 11:00 AM to 3:00 PM."},
                            {"text": "The broker will reject any orders placed in the afternoon", "is_correct": False, "explanation": "Orders execute throughout the open session."},
                            {"text": "Candles only change color after midnight", "is_correct": False, "explanation": "Candles update in real time with each trade match."},
                        ],
                    }
                ],
            },
            {
                "order": 17,
                "title": "Interactive Exercises and Comprehensive Quiz",
                "slug": "interactive-exercises-and-quiz",
                "estimated_minutes": 7,
                "content": """# Comprehensive Candlestick Mastery Quiz

Congratulations on completing all 16 lessons of **Understanding Candlestick Charts**!

You now possess the foundational technical literacy required to decode price action on the Nepal Stock Exchange.

---

### Summary Checklist Before Testing Yourself

1. **OHLC:** Open, High, Low, Close form the foundation of every period.
2. **Body:** Represents conviction; color indicates net directional victor.
3. **Wicks:** Long shadows signify price rejection by bulls or bears.
4. **Bullish Reversals:** Hammer, Inverted Hammer, Bullish Engulfing, Morning Star.
5. **Bearish Reversals:** Shooting Star, Hanging Man, Bearish Engulfing, Evening Star.
6. **Indecision:** Doji and Spinning Top call for patience and confirmation.
7. **Execution:** Always seek volume confirmation and respect your risk limits!

---

Complete the interactive quiz below to verify your mastery and earn your tutorial completion badge!
""",
                "quizzes": [
                    {
                        "question": "Which three-candle pattern features a tall red candle, a small star at the bottom, and a green candle closing at least 50% into the first day's body?",
                        "explanation": "The Morning Star consists of a tall red candle, a star gap/lower body, and a bullish green candle recovering over half of Day 1's decline.",
                        "options": [
                            {"text": "Morning Star", "is_correct": True, "explanation": "Correct! It heralds a bullish dawn."},
                            {"text": "Evening Star", "is_correct": False, "explanation": "Evening star occurs at the top of an uptrend and is bearish."},
                            {"text": "Three Black Crows", "is_correct": False, "explanation": "Three Black Crows is a series of three declining red candles."},
                            {"text": "Bullish Harami", "is_correct": False, "explanation": "A Harami is a two-candle pattern."},
                        ],
                    },
                    {
                        "question": "If an asset experiences a long lower wick during a test of support and closes near the highs, what does this tell us?",
                        "explanation": "A long lower shadow indicates that sellers were unable to sustain prices at lower levels because aggressive buying absorbed all supply.",
                        "options": [
                            {"text": "Sellers attempted to push prices down but buyers forcefully rejected lower prices", "is_correct": True, "explanation": "Correct! Lower shadows signify buyer defense and rejection of lows."},
                            {"text": "Buyers were completely absent from the market", "is_correct": False, "explanation": "Buyers were the ones who pushed price back to the top."},
                            {"text": "The market is guaranteed to enter a 10-year bear market", "is_correct": False, "explanation": "Lower rejection at support is bullish in nature."},
                            {"text": "The candle is an Evening Star", "is_correct": False, "explanation": "Evening Star is a 3-candle top reversal."},
                        ],
                    },
                    {
                        "question": "Where should a prudent trader typically place their protective stop-loss when entering on a Hammer pattern?",
                        "explanation": "A stop-loss is placed just below the low of the Hammer's lower shadow, because a breach of that low invalidates the bullish thesis.",
                        "options": [
                            {"text": "Just below the lowest point of the Hammer's lower shadow", "is_correct": True, "explanation": "Correct! If price drops below that low, the pattern has failed."},
                            {"text": "100% below the current market price", "is_correct": False, "explanation": "That would mean taking a 100% loss."},
                            {"text": "At the previous all-time high", "is_correct": False, "explanation": "Stop losses for long trades must be placed below the entry price, not above."},
                            {"text": "Stop-losses are never used in technical analysis", "is_correct": False, "explanation": "Risk management is the single most important habit of successful traders."},
                        ],
                    },
                ],
            },
        ]

        self.stdout.write("Creating 17 lessons with quizzes...")

        for item in lessons_data:
            lesson, _ = TutorialLesson.objects.update_or_create(
                tutorial=tutorial,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "content": item["content"],
                    "display_order": item["order"],
                    "estimated_minutes": item["estimated_minutes"],
                    "is_published": True,
                },
            )

            # Clear existing quizzes for clean idempotent updates
            lesson.quizzes.all().delete()

            for q_idx, quiz_data in enumerate(item.get("quizzes", []), start=1):
                quiz = TutorialQuiz.objects.create(
                    lesson=lesson,
                    question=quiz_data["question"],
                    explanation=quiz_data.get("explanation", ""),
                    display_order=q_idx,
                )

                for opt_idx, opt_data in enumerate(quiz_data.get("options", []), start=1):
                    TutorialQuizOption.objects.create(
                        quiz=quiz,
                        option_text=opt_data["text"],
                        is_correct=opt_data["is_correct"],
                        explanation=opt_data.get("explanation", ""),
                        display_order=opt_idx,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded tutorial '{tutorial.title}' with {len(lessons_data)} lessons!"
            )
        )

        # ---------------------------------------------------------------------
        # 4. Tutorial 2: Fundamental Analysis: Reading Bank Financials & Ratios
        # ---------------------------------------------------------------------
        self.stdout.write("Seeding Fundamental Analysis Tutorial...")
        fund_tut, _ = Tutorial.objects.update_or_create(
            slug="fundamental-analysis-bank-financials",
            defaults={
                "category": fund_cat,
                "title": "Fundamental Analysis: Reading Bank Financials & Ratios",
                "short_description": "Master banking metrics on NEPSE. Learn how to analyze NPL, CD Ratio, EPS, P/E, Book Value, and evaluate dividend capacity from quarterly reports.",
                "content": (
                    "Welcome to **Fundamental Analysis: Reading Bank Financials & Ratios**.\n\n"
                    "Commercial banks and financial institutions form the backbone of the Nepal Stock Exchange (NEPSE). Unlike non-financial corporations, banks require specialized analytical tools to assess credit risk, liquidity, and true profitability.\n\n"
                    "### What You Will Learn:\n"
                    "- How to read commercial bank balance sheets: Paid-up Capital, Reserves, and Deposit-Loan structures.\n"
                    "- Core valuation multiples: P/E Ratio, Earnings Per Share (EPS), and Price-to-Book (P/B).\n"
                    "- Regulatory and health metrics: Non-Performing Loans (NPL), Credit-to-Deposit (CD) Ratio, and Capital Adequacy Ratio (CAR).\n"
                    "- How to extract Distributable Profit from quarterly unaudited financial statements.\n"
                    "- Analyzing bonus shares vs. cash dividends."
                ),
                "difficulty": Tutorial.DIFFICULTY_INTERMEDIATE,
                "estimated_minutes": 35,
                "display_order": 2,
                "is_featured": True,
                "is_published": True,
            },
        )

        fund_lessons = [
            {
                "order": 1,
                "title": "Commercial Bank Balance Sheet Structure",
                "slug": "bank-balance-sheet-structure",
                "estimated_minutes": 6,
                "content": """# Commercial Bank Balance Sheet Structure

Analyzing a commercial bank on NEPSE is fundamentally different from analyzing manufacturing or hydropower firms. A bank's primary inventory is **money itself**.

---

### 1. Key Liabilities (Where Funds Come From)
- **Deposits:** Savings, fixed deposits (FD), and call deposits from retail and corporate clients. This is the bank's cheapest source of funding.
- **Borrowings:** Interbank borrowing from the Nepal Rastra Bank (NRB) or international development finance institutions.
- **Paid-Up Capital:** The total nominal value of shares issued (minimum NPR 800 Crore for 'A' class commercial banks).
- **Reserves & Surplus:** Accumulated retained earnings and general reserves.

---

### 2. Key Assets (Where Money Goes)
- **Loans & Advances:** The core income-generating engine (home loans, business credit, working capital).
- **Investments:** Government treasury bills, NRB bonds, and equity holdings.
- **Cash & Bank Balance:** Regulatory liquid reserves kept with NRB (Cash Reserve Ratio - CRR).

$$\\text{Total Assets} = \\text{Total Liabilities} + \\text{Shareholders' Equity}$$
""",
                "quizzes": [
                    {
                        "question": "What is the primary liability on a commercial bank's balance sheet?",
                        "explanation": "Customer deposits (savings, fixed, call) constitute the largest liability that a bank uses to fund loans.",
                        "options": [
                            {"text": "Customer Deposits", "is_correct": True, "explanation": "Correct! Deposits belong to customers and are liabilities for the bank."},
                            {"text": "Loans and Advances", "is_correct": False, "explanation": "Loans are assets because borrowers owe money to the bank."},
                            {"text": "Office Buildings", "is_correct": False, "explanation": "Physical assets are fixed assets."},
                            {"text": "Broker Commission Fees", "is_correct": False, "explanation": "Brokers are separate intermediaries."},
                        ],
                    }
                ],
            },
            {
                "order": 2,
                "title": "Core Valuation Ratios: EPS, P/E, and Book Value",
                "slug": "core-valuation-ratios-eps-pe-book-value",
                "estimated_minutes": 6,
                "content": """# Core Valuation Ratios: EPS, P/E, and Book Value

To determine whether a bank's stock is fairly priced on NEPSE, investors utilize standardized per-share metrics.

---

### 1. Earnings Per Share (EPS)
$$\\text{EPS} = \\frac{\\text{Net Profit after Tax}}{\\text{Total Number of Outstanding Shares}}$$
Annualized EPS provides the baseline earning power of one share of stock.

---

### 2. Price-to-Earnings Ratio (P/E)
$$\\text{P/E Ratio} = \\frac{\\text{Current Market Price (LTP)}}{\\text{Annualized EPS}}$$
- **Meaning:** How many rupees investors are willing to pay for every NPR 1 of company profit.
- On NEPSE, mature commercial banks historically trade between a P/E of **12x and 22x** depending on interest rate cycles.

---

### 3. Net Worth / Book Value Per Share (BVPS)
$$\\text{BVPS} = \\frac{\\text{Paid-Up Capital} + \\text{Reserves and Surplus}}{\\text{Total Number of Outstanding Shares}}$$
If a stock's market price trades close to or below its Book Value per Share ($P/B \\le 1.0$), it can signal extreme undervaluation or balance sheet distress.
""",
                "quizzes": [
                    {
                        "question": "If a bank's LTP is NPR 300 and its annualized EPS is NPR 20, what is its P/E ratio?",
                        "explanation": "P/E is 300 / 20 = 15.",
                        "options": [
                            {"text": "15x", "is_correct": True, "explanation": "Correct! 300 / 20 = 15."},
                            {"text": "25x", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "6x", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "60x", "is_correct": False, "explanation": "Incorrect."},
                        ],
                    }
                ],
            },
            {
                "order": 3,
                "title": "Health Metrics: NPL, CD Ratio, and CAR",
                "slug": "health-metrics-npl-cd-ratio-car",
                "estimated_minutes": 7,
                "content": """# Banking Health Metrics: NPL, CD Ratio, and CAR

Nepal Rastra Bank (NRB) imposes strict prudential regulations on all licensed banking institutions.

---

### 1. Non-Performing Loan Ratio (NPL)
$$\\text{NPL Ratio} = \\frac{\\text{Overdue Loans (Substandard + Doubtful + Loss)}}{\\text{Total Loan Portfolio}} \\times 100\\%$$
- **Regulatory Limit:** NRB mandates an NPL under 5%.
- **Impact on Profit:** High NPL forces the bank to set aside heavy loan loss provisions, drastically reducing distributable profits.

---

### 2. Credit to Deposit Ratio (CD Ratio)
$$\\text{CD Ratio} = \\frac{\\text{Total Loans}}{\\text{Total Deposits}} \\times 100\\%$$
- **NRB Ceiling:** Maximum **90%**.
- If a bank has an 89% CD ratio, it cannot expand its lending portfolio without mobilizing new deposits first.

---

### 3. Capital Adequacy Ratio (CAR)
Ensures the bank holds sufficient equity capital to absorb unexpected loan defaults (minimum regulatory benchmark ~11% including buffer).
""",
                "quizzes": [
                    {
                        "question": "What is the regulatory ceiling set by Nepal Rastra Bank for a bank's CD ratio?",
                        "explanation": "NRB regulations require banks to maintain their CD ratio at or below 90%.",
                        "options": [
                            {"text": "90%", "is_correct": True, "explanation": "Correct! 90% is the regulatory maximum."},
                            {"text": "50%", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "100%", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "75%", "is_correct": False, "explanation": "Incorrect."},
                        ],
                    }
                ],
            },
            {
                "order": 4,
                "title": "Quarterly Reports & Distributable Profit",
                "slug": "quarterly-reports-distributable-profit",
                "estimated_minutes": 6,
                "content": """# Analyzing Quarterly Reports & Distributable Profit

Nepali listed companies publish unaudited quarterly financial reports within 30 days of each quarter's close:
- **Q1:** Ashoj end (Mid-October)
- **Q2:** Poush end (Mid-January)
- **Q3:** Chaitra end (Mid-April)
- **Q4:** Ashadh end (Mid-July)

---

### Net Profit vs. Distributable Profit

Beginners often make the grave mistake of looking only at **Net Profit**. However, on NEPSE:
> **Dividends can ONLY be paid out of Distributable Profit!**

NRB mandates that banks must allocate mandatory deductions before calculating distributable profit:
1. **General Reserve:** 20% of net profit.
2. **Regulatory Reserve:** Accrued interest not yet realized in cash.
3. **Staff Welfare Fund & CSR Reserve:** 1% each.

Always check the line item labeled:
$$\\text{Distributable Profit (or Free Cash for Distribution)}$$
Divided by total shares, this yields the **Distributable EPS (Dividend Capacity)**.
""",
                "quizzes": [
                    {
                        "question": "Why is Distributable Profit more important than Net Profit when assessing dividend potential on NEPSE?",
                        "explanation": "Nepali banking law and NRB directives require mandatory statutory transfers, so dividends can only be distributed from free distributable profit.",
                        "options": [
                            {"text": "Dividends can only be paid out of Distributable Profit after statutory reserve transfers", "is_correct": True, "explanation": "Exactly right! Distributable profit determines genuine dividend capacity."},
                            {"text": "Because Net Profit includes cash in employees' pockets", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "Because Distributable Profit is tax-free", "is_correct": False, "explanation": "Tax is already accounted for."},
                            {"text": "Distributable Profit is determined by broker votes", "is_correct": False, "explanation": "It is an audited accounting figure."},
                        ],
                    }
                ],
            },
            {
                "order": 5,
                "title": "Bonus Shares vs. Cash Dividends",
                "slug": "bonus-shares-vs-cash-dividends",
                "estimated_minutes": 6,
                "content": """# Bonus Shares vs. Cash Dividends

One of the most unique aspects of the Nepal Stock Exchange is investor enthusiasm for **Bonus Shares (Stock Dividends)**.

---

### 1. What Are Bonus Shares?
Additional shares given to existing shareholders for free by capitalizing the company's accumulated reserves.
- **Example:** A 10% bonus share on 100 shares means you receive 10 new shares (total 110 shares).
- **Price Adjustment:** NEPSE automatically adjusts the market price on book closure date:
$$\\text{Adjusted Price} = \\frac{\\text{Market Price}}{1 + \\text{Bonus Ratio}}$$

---

### 2. Cash Dividend
A direct deposit of cash profits into the investor's bank account linked via C-ASBA/BOID.

---

### 3. The Dilution Trade-off
While bonus shares increase your total share count, they also **dilute future EPS** if the bank cannot grow its net profit at the same rate as its expanded capital base.
""",
                "quizzes": [
                    {
                        "question": "If a stock trading at NPR 440 announces a 10% bonus share, what will the adjusted opening price be on NEPSE book closure date?",
                        "explanation": "Adjusted price = 440 / (1 + 0.10) = 440 / 1.10 = NPR 400.",
                        "options": [
                            {"text": "NPR 400.00", "is_correct": True, "explanation": "Correct! 440 / 1.10 = NPR 400."},
                            {"text": "NPR 396.00", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "NPR 440.00", "is_correct": False, "explanation": "The price must adjust downward to reflect new share creation."},
                            {"text": "NPR 484.00", "is_correct": False, "explanation": "Incorrect."},
                        ],
                    }
                ],
            },
        ]

        for item in fund_lessons:
            lesson, _ = TutorialLesson.objects.update_or_create(
                tutorial=fund_tut,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "content": item["content"],
                    "display_order": item["order"],
                    "estimated_minutes": item["estimated_minutes"],
                    "is_published": True,
                },
            )
            lesson.quizzes.all().delete()
            for q_idx, quiz_data in enumerate(item.get("quizzes", []), start=1):
                quiz = TutorialQuiz.objects.create(
                    lesson=lesson,
                    question=quiz_data["question"],
                    explanation=quiz_data.get("explanation", ""),
                    display_order=q_idx,
                )
                for opt_idx, opt_data in enumerate(quiz_data.get("options", []), start=1):
                    TutorialQuizOption.objects.create(
                        quiz=quiz,
                        option_text=opt_data["text"],
                        is_correct=opt_data["is_correct"],
                        explanation=opt_data.get("explanation", ""),
                        display_order=opt_idx,
                    )

        # ---------------------------------------------------------------------
        # 5. Tutorial 3: Risk Management & Position Sizing on NEPSE
        # ---------------------------------------------------------------------
        self.stdout.write("Seeding Risk Management Tutorial...")
        risk_tut, _ = Tutorial.objects.update_or_create(
            slug="risk-management-position-sizing",
            defaults={
                "category": risk_cat,
                "title": "Risk Management & Position Sizing on NEPSE",
                "short_description": "Protect your capital. Master the 1% risk rule, mathematical position sizing in Nepalese Rupees, managing the T+2 settlement risk, and avoiding emotional FOMO traps.",
                "content": (
                    "Welcome to **Risk Management & Position Sizing on NEPSE**.\n\n"
                    "Most traders focus 90% of their effort on stock selection and only 10% on risk management. In reality, professional profitability is 90% risk management and position sizing.\n\n"
                    "### What You Will Learn:\n"
                    "- The 1% and 2% Golden Rules of capital preservation.\n"
                    "- Step-by-step formula to calculate your share quantity based on stop loss distance.\n"
                    "- Navigating the T+2 clearing cycle and liquidity traps in illiquid scrips.\n"
                    "- Managing risk-to-reward ratios (R:R >= 1:2).\n"
                    "- Overcoming psychological biases: Averaging down on losing stocks and FOMO chasing."
                ),
                "difficulty": Tutorial.DIFFICULTY_BEGINNER,
                "estimated_minutes": 30,
                "display_order": 3,
                "is_featured": False,
                "is_published": True,
            },
        )

        risk_lessons = [
            {
                "order": 1,
                "title": "The 1% Rule of Capital Preservation",
                "slug": "one-percent-rule-capital-preservation",
                "estimated_minutes": 5,
                "content": """# The 1% Rule of Capital Preservation

The fundamental law of survival in financial markets is simple:
> **Never risk more than 1% to 2% of your total trading capital on any single trade.**

---

### Why Math Protects You
If your total trading portfolio is **NPR 500,000**:
- **1% Risk:** NPR 5,000 maximum loss per trade.
- Even if you experience 5 consecutive losing trades, your portfolio drops to NPR 475,000 (a manageable 5% drawdown).
- If you risk 20% per trade, 3 bad trades wipe out nearly half your capital!

$$\\text{Maximum Rupee Risk} = \\text{Total Portfolio Value} \\times 0.01$$
""",
                "quizzes": [
                    {
                        "question": "If your total NEPSE trading capital is NPR 1,000,000, what is the maximum amount you should risk losing on a single trade under the 1% rule?",
                        "explanation": "1% of NPR 1,000,000 is NPR 10,000.",
                        "options": [
                            {"text": "NPR 10,000", "is_correct": True, "explanation": "Correct! 1% of 1,000,000 is 10,000."},
                            {"text": "NPR 100,000", "is_correct": False, "explanation": "That is 10%, which is dangerously high."},
                            {"text": "NPR 50,000", "is_correct": False, "explanation": "That is 5%."},
                            {"text": "NPR 1,000", "is_correct": False, "explanation": "That is 0.1%."},
                        ],
                    }
                ],
            },
            {
                "order": 2,
                "title": "Calculating Position Size in Nepalese Rupees",
                "slug": "calculating-position-size-nepalese-rupees",
                "estimated_minutes": 6,
                "content": """# Calculating Position Size in Nepalese Rupees

Position sizing answers the critical question:
> *"How many shares should I buy?"*

Never guess or buy arbitrary round numbers like 500 or 1,000 kitta. Use the scientific formula:

$$\\text{Position Size (Shares)} = \\frac{\\text{Maximum Allowed Rupee Risk}}{\\text{Entry Price} - \\text{Stop Loss Price}}$$

---

### Step-by-Step Example

1. **Portfolio:** NPR 600,000.
2. **1% Risk Limit:** NPR 6,000.
3. **Stock Setup:**
   - Entry: NPR 400.00
   - Technical Stop Loss (below support): NPR 380.00
   - Risk per share: $400 - 380 = \\text{NPR } 20.00$
4. **Calculated Quantity:**
   $$\\text{Quantity} = \\frac{6,000}{20} = 300 \\text{ shares}$$

Total investment: $300 \\times 400 = \\text{NPR } 120,000$.
If the stock drops to 380 and triggers your stop-loss, your total loss is exactly NPR 6,000 (your planned 1% limit).
""",
                "quizzes": [
                    {
                        "question": "If your max allowed risk is NPR 4,000, your entry is NPR 500, and your stop-loss is NPR 480, how many shares should you buy?",
                        "explanation": "Risk per share = 500 - 480 = 20. Position size = 4,000 / 20 = 200 shares.",
                        "options": [
                            {"text": "200 shares", "is_correct": True, "explanation": "Correct! 4,000 / 20 = 200 shares."},
                            {"text": "100 shares", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "500 shares", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "1,000 shares", "is_correct": False, "explanation": "Incorrect."},
                        ],
                    }
                ],
            },
            {
                "order": 3,
                "title": "Understanding the T+2 Clearing Risk on NEPSE",
                "slug": "t2-clearing-risk-nepse",
                "estimated_minutes": 6,
                "content": """# Understanding the T+2 Clearing Risk on NEPSE

In many international markets, day traders can buy at 10:00 AM and sell at 10:05 AM if the trade goes against them.

**On NEPSE, you CANNOT exit immediately.**

---

### The Nepal Settlement Reality
- Shares bought on **Sunday (T)** are transferred to your Demat/MeroShare on **Tuesday evening (T+2)**.
- You can only sell them on **Wednesday morning (T+3)**.
- During these 2 trading days, you are locked into the position and exposed to gap-downs or negative macroeconomic news.

### How to Mitigate T+2 Risk
1. Avoid buying highly volatile speculative micro-caps near circuit highs.
2. Only take setups where multi-day technical support is sturdy.
3. Keep individual stock allocations at reasonable portfolio weights.
""",
                "quizzes": [
                    {
                        "question": "Why is stop-loss execution different on NEPSE compared to markets with instant intraday trading?",
                        "explanation": "Due to Nepal's T+2 settlement cycle, shares purchased cannot be sold until they settle into your Demat account, meaning you cannot cut losses intraday on Day 1 or Day 2.",
                        "options": [
                            {"text": "Shares cannot be sold until they settle into your Demat account (T+2), locking you in temporarily", "is_correct": True, "explanation": "Correct! Settlement lockup is a vital structural risk to manage."},
                            {"text": "Brokers choose which shares to sell for you", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "NEPSE does not have any price movements during the week", "is_correct": False, "explanation": "Incorrect."},
                            {"text": "T+2 means you receive a 2% discount on each trade", "is_correct": False, "explanation": "T+2 is the settlement cycle, not a discount."},
                        ],
                    }
                ],
            },
        ]

        for item in risk_lessons:
            lesson, _ = TutorialLesson.objects.update_or_create(
                tutorial=risk_tut,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "content": item["content"],
                    "display_order": item["order"],
                    "estimated_minutes": item["estimated_minutes"],
                    "is_published": True,
                },
            )
            lesson.quizzes.all().delete()
            for q_idx, quiz_data in enumerate(item.get("quizzes", []), start=1):
                quiz = TutorialQuiz.objects.create(
                    lesson=lesson,
                    question=quiz_data["question"],
                    explanation=quiz_data.get("explanation", ""),
                    display_order=q_idx,
                )
                for opt_idx, opt_data in enumerate(quiz_data.get("options", []), start=1):
                    TutorialQuizOption.objects.create(
                        quiz=quiz,
                        option_text=opt_data["text"],
                        is_correct=opt_data["is_correct"],
                        explanation=opt_data.get("explanation", ""),
                        display_order=opt_idx,
                    )

        self.stdout.write(
            self.style.SUCCESS("All tutorials, lessons, and quizzes seeded successfully!")
        )
