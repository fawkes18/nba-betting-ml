import pandas as pd

def get_url(row):
    year_idx = None
    if str(row["date"])[:2] == "12" and len(str(row["date"])) == 4:
        year_idx = "2020"
    else:
        year_idx = "20210"
    
    md_idx = str(row["date"])
        
    date_str = f"{year_idx}{md_idx}0"
    home_abbrev = row["home_abbrev"]
    
    final_url = f"https://www.basketball-reference.com/boxscores/pbp/{date_str}{home_abbrev}.html"
    return final_url

def calc_split_results(qstart, qsplit, qend, udx, fdx):
    ud_start, fv_start = int(qstart.split("-")[udx]), int(qstart.split("-")[fdx])
    ud_split, fv_split = int(qsplit.split("-")[udx]), int(qsplit.split("-")[fdx])
    ud_end, fv_end = int(qend.split("-")[udx]), int(qend.split("-")[fdx])
    
    fv_score_first = fv_split - fv_start
    ud_score_first = ud_split - ud_start
    
    if ud_score_first > fv_score_first:
        ud_won_first = True
    else:
        ud_won_first = False
        
    fv_score_second = fv_end - fv_split
    ud_score_second = ud_end - ud_split
    
    if ud_score_second > fv_score_second:
        ud_won_second = True
    else:
        ud_won_second = False
        
    return ud_won_first, ud_won_second

def get_6min_segment_results(play_table, udx, fdx):
    q1s = 1
    q1e = play_table["Score"].tolist().index("End of 1st quarter")

    q2s = q1e + 4
    q2e = play_table["Score"].tolist().index("End of 2nd quarter")

    q3s = q2e + 4
    q3e = play_table["Score"].tolist().index("End of 3rd quarter")
    
    q1 = play_table.iloc[q1s:q3e,]
    q2 = play_table.iloc[q2s:q2e,]
    q3 = play_table.iloc[q3s:q3e,]

    s1 = [rtime.split(":")[0] for rtime in q1["Time"].tolist()].index("5")
    s2 = [rtime.split(":")[0] for rtime in q2["Time"].tolist()].index("5")
    s3 = [rtime.split(":")[0] for rtime in q3["Time"].tolist()].index("5")
    
    q1_results = calc_split_results(q1["Score"].tolist()[0], q1["Score"].tolist()[s1], q1["Score"].tolist()[-1], udx, fdx)
    q2_results = calc_split_results(q2["Score"].tolist()[0], q2["Score"].tolist()[s2], q2["Score"].tolist()[-1], udx, fdx)
    q3_results = calc_split_results(q3["Score"].tolist()[0], q3["Score"].tolist()[s3], q3["Score"].tolist()[-1], udx, fdx)
    
    return q1_results, q2_results, q3_results

def get_avg_score_difference(scores, udx, fdx, q4_idx):
    score_splits = list(set(scores))
    score_differences = []

    for score in score_splits[:q4_idx]:
        try:
            ud_score, fv_score = int(score.split("-")[udx]), int(score.split("-")[fdx])
            diff = ud_score - fv_score
            score_differences.append(diff)
        except Exception as e:
            pass
    
    avg_difference = sum(score_differences) / len(score_differences)
    
    max_difference_pos = max(score_differences)
    max_difference_neg = min(score_differences)
    
    return avg_difference, max_difference_pos, max_difference_neg

improved_feature_list = []

for index, row in odds.iterrows():
    url = get_url(row) 
    try:
        game = pd.read_html(url)[0]
        game.columns = [col[1] for col in game.columns]
                
        score_list = game["Score"].tolist()
        
        q2_idx = score_list.index("Start of 2nd quarter")
        q3_idx = score_list.index("Start of 3rd quarter")
        q4_idx = score_list.index("Start of 4th quarter")
        
        q1_results = score_list[q2_idx-4]
        q2_results = score_list[q3_idx-4]
        q3_results = score_list[q4_idx-4]
        q4_results = score_list[-2]
        
        udx = 0
        fdx = 1
        
        if row["home_favored"] == False:
            udx = 1
            fdx = 0
                   
        q1_segment_results, q2_segment_results, q3_segment_results = get_6min_segment_results(game, udx, fdx)
        avg_score_difference, max_score_difference_pos, max_score_difference_neg = get_avg_score_difference(score_list, udx, fdx, q4_idx)
            
        q1_dif = int(q1_results.split("-")[udx]) - int(q1_results.split("-")[fdx])
        q2_dif = int(q2_results.split("-")[udx]) - int(q2_results.split("-")[fdx])
        q3_dif = int(q3_results.split("-")[udx]) - int(q3_results.split("-")[fdx])
        q4_dif = int(q4_results.split("-")[udx]) - int(q4_results.split("-")[fdx])
                                
        if q3_dif < 0: 
            improved_score = False
            if q4_dif > q3_dif:
                improved_score = True

            score_change = q4_dif + np.absolute(q3_dif)

            improved_features = {
                "mid": row["mid"],
                "q1_diff": q1_dif, 
                "q2_diff": q2_dif,
                "q3_diff": q3_dif,
                "improved_score": improved_score,
                "score_change": score_change,
                "q1_first": q1_segment_results[0],
                "q1_second": q1_segment_results[1],
                "q2_first": q2_segment_results[0],
                "q2_second": q2_segment_results[1],
                "q3_first": q3_segment_results[0],
                "q3_second": q3_segment_results[1],
                "avg_score_diff": avg_score_difference,
                "max_score_diff_pos": max_score_difference_pos,
                "max_score_diff_neg": max_score_difference_neg
                }
            improved_feature_list.append(improved_features)
        
    except Exception as e:
        print(e)
        
df = pd.DataFrame(improved_feature_list)
