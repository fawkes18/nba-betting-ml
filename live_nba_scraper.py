import boto
import pandas as pd 
import requests



class BoxScoreScraper:
    def __init__(self, game_url: str, home_favored: bool):
        self.game_url = game_url
        self.home_favored = home_favored
        
    def send_request(self) -> dict:
        """Send request to the NBA API to receive the live boxscore data of the game"""
        r = requests.get(self.game_url)
        json_data = r.json()
        return json_data
    
    def set_meta_info(self, json_data: dict) -> str:
        """
        Extract Information about date and the hometeam in order to set unique identifier for game.
        Unique identifier consists of the following parts:
        - 3 Letter Team Abbreviation (as string)
        - Month (as numeric)
        - Day (as numeric)
        """
        team_abbrev = json_data["game"]["gameCode"].split("/")[-1][3:]
        date_meta_info = json_data["meta"]["time"]
        mid = team_abbrev + date_meta_info.split("-")[1] + date_meta_info.split("-")[2].split()[0] 
        return mid
    
    def extract_shooting_stats(self, json_data: dict, team_status: str) -> str:
        """Extract shooting stats """
        pct_fg = json_data["game"][team_status]["statistics"]["fieldGoalsPercentage"]
        pct_3p = json_data["game"][team_status]["statistics"]["threePointersPercentage"]
        pct_ft = json_data["game"][team_status]["statistics"]["freeThrowsPercentage"]
        return pct_fg, pct_3p, pct_ft
    
    def get_max_score_differences(self, json_data: dict, team_status: str) -> str:
        """Extract the highest and lowest score difference of the team"""
        max_score_diff_pos = json_data["game"][team_status]["statistics"]["biggestLead"]
        if team_status == "homeTeam":
            max_score_diff_neg = json_data["game"]["awayTeam"]["statistics"]["biggestLead"]
        else:
            max_score_diff_neg = json_data["game"]["homeTeam"]["statistics"]["biggestLead"]
        
        return max_score_diff_pos, max_score_diff_neg
    
    def get_active_players(self, json_data: dict, team_status: str) -> list:
        """Get a list of all the active players of the team"""
        active_players = []
        
        for player in json_data["game"][team_status]["players"]:
            if player["status"] == "INACTIVE":
                continue
            
            active_players.append(player["name"])
            
        return active_players
    
    def get_boxscore_stats(self) -> dict:
        """Create dictionary with all the required features"""
        json_data = self.send_request()
        
        if self.home_favored:
            team_status = "awayTeam"
        else:
            team_status = "homeTeam"
    
        mid = self.set_meta_info(json_data)
        max_score_diff_pos, max_score_diff_neg = self.get_max_score_differences(json_data, team_status)
        pct_fg, pct_3p, pct_ft = self.extract_shooting_stats(json_data, team_status)
        active_players = self.get_active_players(json_data, team_status)
        
        boxscore_features = {
            "mid": mid,
            "max_score_diff_pos": max_score_diff_pos,
            "max_score_diff_neg": max_score_diff_neg,
            "pct_3p": pct_3p,
            "pct_fg": pct_fg,
            "pct_ft": pct_ft,
            "active_players": active_players
        }
        
        return boxscore_features



class PlayByPlayScraper:
    def __init__(self, game_url: str, home_favored: bool, team_abbrev: str):
        self.game_url = game_url
        self.home_favored = home_favored
        self.team_abbrev = team_abbrev
        
    def send_request(self):
        """Send request to the NBA API to receive the live boxscore data of the game"""
        r = requests.get(self.game_url)
        json_data = r.json()
        return json_data
    
    def get_avg_score_diff(self, json_data) -> str:
        scores = []
        score_differences = []

        for action in play_by_play["game"]["actions"]:
            score_home = action["scoreHome"]
            score_away = action["scoreAway"]

            score = f"{score_home}-{score_away}"
            score_difference = int(score_home) - int(score_away)
            if score not in scores:
                scores.append(score)
                score_differences.append(score_difference)

        avg_score_diff = sum(score_differences) / len(score_differences)

        if self.home_favored:
            if avg_score_diff <= 0:
                return np.absolute(avg_score_diff)
            else:
                return -avg_score_diff
        else:
            return avg_score_diff
                
    
    def get_quarter_results(self, json_data, idxs) -> str:
        q1_result = f'{json_data["game"]["actions"][idxs[0]]["scoreHome"]}-{json_data["game"]["actions"][idxs[0]]["scoreAway"]}'
        q2_result = f'{json_data["game"]["actions"][idxs[1]]["scoreHome"]}-{json_data["game"]["actions"][idxs[1]]["scoreAway"]}'
        q3_result = f'{json_data["game"]["actions"][idxs[2]]["scoreHome"]}-{json_data["game"]["actions"][idxs[2]]["scoreAway"]}'

        return q1_result, q2_result, q3_result
    
    
    def get_quarter_splits(self, json_data: dict) -> str:
        compare_period = 1

        q1_split = None
        q2_split = None
        q3_split = None

        quarter_idxs = []

        for i, action in enumerate(json_data["game"]["actions"]):
            current_period = action["period"]

            if current_period != compare_period:
                quarter_idxs.append(i-1)

            compare_period = action["period"]

            game_minute = action["clock"][2:4]
            if game_minute == "05":
                if current_period == 1:
                    if not q1_split:
                        q1_split = f'{action["scoreHome"]}-{action["scoreAway"]}'

                if current_period == 2:
                    if not q2_split:
                        q2_split = f'{action["scoreHome"]}-{action["scoreAway"]}'

                if current_period == 3:
                    if not q3_split:
                        q3_split = f'{action["scoreHome"]}-{action["scoreAway"]}'

        q1_result, q2_result, q3_result = self.get_quarter_results(json_data, quarter_idxs)

        return q1_result, q2_result, q3_result, q1_split, q2_split, q3_split
    
    def get_segment_results(self, start_score: str, end_score: str) -> bool:
        home_start, away_start = int(start_score.split("-")[0]), int(start_score.split("-")[1])
        home_end, away_end = int(end_score.split("-")[0]), int(end_score.split("-")[1])

        home_improv, away_improv = home_end - home_start, away_end - away_start

        if self.home_favored:
            if away_improv >= home_improv:
                return True
            else:
                return False
        else:
            if home_improv >= away_improv:
                return True
            else:
                return False
        

    def get_score_data(self) -> dict:
        json_data = self.send_request()
        
        q1_result, q2_result, q3_result, q1_split, q2_split, q3_split = self.get_quarter_splits(json_data)
        avg_score_diff = self.get_avg_score_diff(json_data)

        q1_diff = int(q1_result.split("-")[0]) - int(q1_result.split("-")[1])
        q2_diff = int(q2_result.split("-")[0]) - int(q2_result.split("-")[1])
        q3_diff = int(q3_result.split("-")[0]) - int(q3_result.split("-")[1])

        q1_first = self.get_segment_results("0-0", q1_split)
        q1_second = self.get_segment_results(q1_split, q1_result)
        q2_first = self.get_segment_results(q1_result, q2_split)
        q2_second = self.get_segment_results(q2_split, q2_result)
        q3_first = self.get_segment_results(q2_result, q3_split)
        q3_second = self.get_segment_results(q3_split, q3_result)

        segment_feature_dict = {
            "avg_score_diff": avg_score_diff,
            "q1_diff": q1_diff,
            "q2_diff": q2_diff,
            "q3_diff": q3_diff,
            "q1_first": q1_first,
            "q1_second": q1_second,
            "q2_first": q2_first,
            "q2_second": q2_second,
            "q3_first": q3_first,
            "q3_second": q3_second
        }

        return segment_feature_dict  

    def get_team_stats(self, active_players: list) -> dict:  
        team_table = pd.read_csv(f"s3://ml-nba-betting/team_stats/{self.team_abbrev}_team_stats.csv")

        important_players = team_table["player_name"].iloc[:3, ].tolist()

        team_fgpct = team_table.iloc[-1]["FG%"]
        team_3pct = team_table.iloc[-1]["3P%"]
        team_ftpct = team_table.iloc[-1]["FT%"]

        if important_players[0] in active_players:
            p1_plays = True
        else:
            p1_plays = False

        if important_players[1] in active_players:
            p2_plays = True
        else:
            p2_plays = False

        if important_players[2] in active_players:
            p3_plays = True
        else:
            p3_plays = False

        team_stats_features = {
            "team_fgpct": team_fgpct,
            "team_3pct": team_3pct,
            "team_ftpct": team_ftpct,
            "p1_plays": p1_plays,
            "p2_plays": p2_plays,
            "p3_plays": p3_plays
        }
    
        return team_stats_features
    
def main() -> None:
    play_url = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_0022100441.json"
    box_url = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022100441.json"
    
    team_abbrev = "det"
    home_favored = False
    
    play_scraper = PlayByPlayScraper(game_url=play_url, team_abbrev=team_abbrev, home_favored=home_favored)
    boxscore_scraper = BoxScoreScraper(game_url=box_url, home_favored=home_favored)
    
    boxscore_dict = boxscore_scraper.get_boxscore_stats()
    by_quarter_dict = play_scraper.get_score_data()
    team_stats_dict = play_scraper.get_team_stats(boxscore_dict["active_players"])
    
    all_features = {**boxscore_dict, **by_quarter_dict, **team_stats_dict}
    del all_features["active_players"]
    
    additional_features = {
        "pct_fg_reg": all_features["pct_fg"] - all_features["team_fgpct"],
        "pct_3p_reg": all_features["pct_3p"] - all_features["team_3pct"],
        "pct_ft_reg": all_features["pct_ft"] - all_features["team_ftpct"]
    }
    
    all_features.update(additional_features)
    
    print(all_features)

        
if __name__ == "__main__":
    main()
