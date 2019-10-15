# NBA-Jump-Balls

Posted on [reddit/r/nba](https://www.reddit.com/r/nba/comments/dhandf/oc_elo_system_to_determine_who_are_the_best_at/), making it to the top of the [front page](https://imgur.com/xzsnckE) at one point!



## Purpose

I created this analysis to measure how well different NBA players perform in jump ball situations. This was inspired by a prop bet I see on various sportsbook, which is "Team to Score First". I felt some of these lines were mispriced, and if I could measure how likely a player was to win a jump ball (and therefore who gets the ball first), I could estimate how likely their team is to score first.

## Methodology

NBA play by play data going back to 2006 was scraped and parsed from stats.nba.com using the [nba_py](https://github.com/seemethere/nba_py/tree/master/nba_py) api. I used only jump balls that occur either at the start of the game, or the start of any overtime period. This is because these are the only jump balls where teams can choose who jumps, as opposed to a live ball situation where the jumpers are just whoever happened to tie up the ball.

The play by play data only has last names in the description, so these had to be mapped to the correct player. These last names could be mapped to player id's from stats.nba.com, but unfortunately the api does not account for players who have moved teams within a season. For a given season it only lists the final team a player played for. Therefore, to account for player movement, I cross-referenced with basketball-reference. With a way to map the play by play descriptions to the correct player id, I can now count the wins and losses of each jump ball and attribute the win/loss to each player.

## Elo Rating

But not all wins and losses are the same. One player could be 3-0 in jump balls vs. only 6'8" centers whereas another could be 0-3 jumping against 7'0 giants. To better measure the relative skill of each player, I used an [Elo Rating System](https://en.wikipedia.org/wiki/Elo_rating_system) to assign a numeric ranking. When a new player enters the league, he is given a ranking of 1500 (the league average) with a provisional period of 15 games. A k-factor of 40 is used. With the Elo ratings calculated, now two players can be compared, and a percentage likelihood of Player A winning the jump can be given.

## Next Steps

I also wanted to see how often a team who gets the ball first actually does score first. Again using the play by play data, I could test for each team and see when they won the jump ball, and when they score first if they did. Looking at the results, the league average rate of scoring first when winning the jump is about 60%.

I ran a [Chi-Square Test of Homogeneity](https://stattrek.com/chi-square-test/homogeneity.aspx) to see if this rate differs for the individual team, and based on a significance value of 0.05 found no significant difference. Thus, I used 60% as a universal value. Future iterations can improve this part of the methodology.

## Results (so far...)

Using this methodology, I've been able to get a rough estimate on the probability of a team scoring first. I've used this to compare to the odds I've seen and made bets and were profitable but over an admittedly small sample size. By the end of the 2018-19 season, finding good opportunities to bet on were getting fewer and far between.
