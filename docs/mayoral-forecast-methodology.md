# How the mayoral forecast is made

The forecast on the homepage comes from one statistical model that is fitted every time the polls are updated. It answers three questions from the same set of simulated elections: how far apart the two leading candidates are likely to finish, what each candidate's share of the vote could look like, and how often each candidate wins the whole race. This page explains the model in plain language. The formal record is ADR 0054, amended by ADR 0055, and the research notes they cite.

## What goes in

- **This year's polls.** Every published poll that asked about the certified field, Olivia Chow, Brad Bradford and Chris Alexander, enters once. Polls taken before the field was certified, with other names on the ballot, are not used; a sensitivity check confirmed they would change the answer by about a point.
- **Seven past campaigns.** The 2003, 2006, 2010, 2014, 2018, 2022 and 2023 Toronto mayoral races, with 97 polls and their results. They are not used to predict 2026 directly. They teach the model four things: how much support typically moves from week to week, how far polling firms typically sit from one another, how far final polls have typically been from the result, and how much of the vote typically goes to minor candidates.
- **Nothing else.** No editorial adjustments, no fundamentals, no judgement about individual candidates.

## What the model does

1. **Where the race stands.** Each candidate's support is tracked as a path through the campaign. Each poll is a noisy reading of that path, with allowance for the firm that ran it and for how many people it asked. Polls disagree, so the current estimate carries a range, roughly plus or minus five points on the gap between the two leaders.
2. **What can still change.** Between the latest poll and election day the path keeps moving, at the pace the past campaigns say is typical for Toronto, with this campaign allowed to be calmer or livelier than average.
3. **How polls miss.** On election day the result differs from the final polling picture. The model treats the result as one more, especially noisy, reading of the electorate, with the noise level learned from the seven past races, where the gap between the leader and the runner-up known at the time was off by about 16 points on average. Larger candidates move by more points than smaller ones, and a fringe candidate's proportional swings do not set the front-runners' uncertainty. This is the largest source of uncertainty in the forecast and the reason a clear polling lead does not translate into a near-certain win.
4. **The rest of the ballot.** The 50 other certified candidates are treated as one pool whose combined share is learned from past races. No single one of them is modelled as a winner.

Steps 1 to 4 are combined into 16,000 simulated elections. Every number on the page is a summary of those simulations, so the margin chart, the vote ranges and the win probabilities always agree with one another.

## What the numbers mean

- **The margin bars** sort the simulations into three outcomes: the poll leader ahead by two points or more, the two within two points of each other, and the challenger ahead by two or more. Each bar carries its share of the simulations. Finishing ahead of one rival is not the same as winning the race.
- **The vote ranges** are the middle 80% of simulated outcomes for each candidate's share of all votes cast. Ranges can overlap; they are not chances of winning.
- **The win probabilities** are the fraction of simulated elections each candidate wins outright. They are rounded to whole percentages, with "<1%" and ">99%" at the extremes.
- **Where the uncertainty comes from** shows the gap between the two leaders under each source of doubt on its own, applied to today's middle estimate: the polls' own noise, five more weeks of campaign movement, and how far results have landed from final polls. A fourth row, set apart, is all three together, which is the published forecast. The chance printed at the right is how often the challenger is ahead in that row. The sources combine roughly as the square root of the sum of squares, not by adding, which is why the last range is wider than any one source but narrower than their sum.

## What the model does not know

It cannot tell which way this year's polls are wrong, only how wrong polls have tended to be. It treats a late surge by a candidate outside the top two the same way past surges have played out, and there have been two in seven races. It has seven past elections to learn from, so its uncertainty about its own uncertainty is real. When the model's numerical checks fail, the previous forecast stays up rather than a broken one being published.

## Checks

Before this model replaced the previous one it was tested by hiding each past election's result in turn and predicting it from the polls available 39 days out (the position of the 2026 race when the model was adopted) and 14 days out. Its 80% ranges for the leader's margin contained the actual margin in ten of eleven cases. The election-day noise model was then chosen by a second test whose pass rule was written down before the candidates were fitted; the version adopted predicted the past elections better than the one it replaced on every measure in that rule, and moved the poll leader's chance from about 63% to about 70%. The full records, the alternatives tried and rejected, and the runtime of the model (about a minute) are in the research notes referenced by ADR 0054 and ADR 0055.
