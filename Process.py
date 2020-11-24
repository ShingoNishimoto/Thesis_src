import copy
from collections import deque


#いるんか？クラス
#コマンドの探索が必要になった段階の第一候補コマンドを受け取る．
#探索の過程にsystemのメソッド使いたい．てことはsystem全体をコピーする必要があるのか？
class Process:
    # processの中で再利用したい情報だけをコピーして持っておく．
    #次のコマンド候補の検索までこっちでやる？→次のコマンドに関してはこの中で
    # Processインスタンスを生成する？
    def __init__(self,sat,COM_ID,previous_candidate,ID):
        processID = ID 
        processID["COM_ID"] = COM_ID
        #hashableにするために
        self.ID = tuple(processID.items())
        #ここで受け取るものは(COM_ID,candidate_TEL_ID)のものだけにする
        self.sat = copy.deepcopy(sat)
        COM = self.sat.COM[COM_ID]
        self.candidates = {}
        for TEL_ID in COM.candidate_TEL_ID:
            #ここにcandidateに入ってるけど中身ないやついる説．
            if not previous_candidate[(COM_ID,TEL_ID)]["COM"] and not previous_candidate[(COM_ID,TEL_ID)]["TEL"]:
                continue
            self.candidates[(COM_ID,TEL_ID)] = previous_candidate[(COM_ID,TEL_ID)]
            #print(candidate[(COM.ID,TEL_ID)])
        #ほんまに全部用意する必要があるのか？これの中身はどこで更新されているのか確認！
        self.total_candidates = {COM_ID : {"COM":[], "TEL":[]} for COM_ID in self.sat.COM.keys()}
        self.result = {}
        self.effectness = {COM_ID : {} for COM_ID in self.sat.COM.keys()}
        self.negative_effect = {COM_ID : {} for COM_ID in self.sat.COM.keys()}
        #next processみたいなものを持っておく，IDをシステム側で管理する？
        #self.

    #コマンドが持つ確認候補があるテレメトリの結果を場合分けする
    # これはテレメトリ一つ一つにしても意味ない感じがする．
    # 確認可能性の高いペアから見ていった木構造を作る．経路ごとの平均確率を使う
    def Process_flow(self):
        # candidateを確率高い順にソート
        candidate_link_list = copy.deepcopy(sorted(self.candidates.items(), key=lambda x:x[1]["P_route"]["average"],reverse=True)) 
        #print(candidate_link_list)
        #これコピー渡さんと他の結果に影響する
        self.result["normal"] = self.calculate_TEL_senario(copy.deepcopy(candidate_link_list),"normal")
        self.result["abnormal"] = self.calculate_TEL_senario(copy.deepcopy(candidate_link_list),"abnormal")
        #ここで初期コマンド結果が正常だったときと異常だった時の結果をまとめて受け取っている．
        #print("normal",self.result["normal"])
        #print("abnormal",self.result["abnormal"])
        #この結果が扱いにくい，知りたいのは最後まで行ったものの全通り
        #辿って行って，next_routeが空になったものが終点であるという判断をすればいいか
        #これを各結果ごとに分けて，ID的なものを割り振った形に直す
        self.devide_each_results()
        #ここには途中結果も入っている
        #print(self.each_result)

    #必要な情報
    #　確率（これは各経路の結果の積（AND）），(normalとかの)結果，どのテレメトリがどの結果になったものか
    # 後で使いたいやり方として，実践結果が同じになるものを検索したい．
    #テレメトリを確認していった途中結果も保持していたいけど．．．
    #とりあえずIDは
    def devide_each_results(self):
        self.each_result = {}
        key_n = (1,)
        #何もない奴
        self.each_result[key_n] = {"history":[],"P":1,"normal_link":{"COM":[],"TEL":[]},\
            "abnormal_link":{"COM":[],"TEL":[]}, "next_processes":[],"Fin":False} #終わったかどうかのフラグ
        self.call_for_devide(list(self.result["normal"].items())[0],"normal",key_n)
        key_a = (0,)
        #何もない奴
        self.each_result[key_a] = {"history":[],"P":1,"normal_link":{"COM":[],"TEL":[]},\
            "abnormal_link":{"COM":[],"TEL":[]}, "next_processes":[],"Fin":False}
        self.call_for_devide(list(self.result["abnormal"].items())[0],"abnormal",key_a)
        
    
    #再帰じゃないと対応できない
    def call_for_devide(self,result_items,result_flag,key):
        #次がないときの処理
        if not result_items:
            return 1
        TEL_ID, result = result_items
        #keyはタプルで階層的に管理
        if len(key)<2:
            p_key = key
        else:
            p_key = key[0:-1]
        #ここで多分テレメトリ全て見たのか判定ができていない
        self.each_result[key] = copy.deepcopy(self.each_result[p_key])
        self.each_result[key]["P"] = self.each_result[p_key]["P"]*result["probability"]
        link_flag = result_flag + "_link"
        self.each_result[key][link_flag] = self.dict_merge(self.each_result[p_key][link_flag],\
            result[link_flag])
        
        key_n = tuple(list(key) + [1])
        key_a = tuple(list(key) + [0])
        
        #normal linkのみ更新がある
        if result_flag=="normal":
            self.each_result[key]["history"].append({TEL_ID:"OK"})
        elif result_flag=="abnormal":
            self.each_result[key]["history"].append({TEL_ID:"NG"})

        #すぐに次の段階へ分岐
        #次があるのか見るのがひつよう
        if result["next_route"]:
            #print(result["next_route"])
            if "normal" in result["next_route"].keys():
                self.call_for_devide(list(result["next_route"]["normal"].items())[0],"normal",key_n)
            if "abnormal" in result["next_route"].keys():
                self.call_for_devide(list(result["next_route"]["abnormal"].items())[0],"abnormal",key_a)
        else:
            #なんでもいい
            self.call_for_devide({},"none",key)
        

    #辞書の結合
    def dict_merge(self,d1,d2):
        merge_dict = d1.copy()
        #{"COM:[],"TEL":[]}の結果を結合している
        for k,v in d1.items():
            merge_dict[k] = v + d2[k]
        return merge_dict


    #テレメトリの結果がそのシナリオの結果になるための確率を計算
    def calculate_TEL_senario(self,candidate_link_list,Tel_result):
        result = {}
        #print(candidate_link_list)
        pair, route = candidate_link_list[0]
        TEL_ID = pair[1]
        result[TEL_ID] = {}
        #その経路で結果が正常or異常になる確率
        # averageの代入だけだと結果に応じた更新ができていない←これ実装できているのか？
        P_tel_normal = 1
        for COMlink in route["COM"]:
            P_tel_normal = P_tel_normal*self.sat.COMlinks[COMlink].probability
        for TELlink in route["TEL"]:
            P_tel_normal = P_tel_normal*self.sat.TELlinks[TELlink].probability
        
        #candidateがテレメの結果によって変わるはずなので引数に応じて分岐させるか．
        if Tel_result=="normal":
            result[TEL_ID]["probability"] = P_tel_normal
        else:
            result[TEL_ID]["probability"] = 1 - P_tel_normal

        #print("before",candidate_link_list)
        self.find_remain_link(result,candidate_link_list,Tel_result)
        #print(Tel_result,"after",candidate_link_list)
        #print(result[TEL_ID])

        #最後の経路.popしているので空
        #結果がnormal, abnormal関係なく次に見るテレメトリは決まるのか？
        result[TEL_ID]["next_route"] = {}
        if not candidate_link_list:
            #print(TEL_ID)
            return result
        else:
            #candidate_link_listを更新
            if Tel_result=="normal":
                result[TEL_ID]["next_route"]["normal"] = self.calculate_TEL_senario(copy.deepcopy(candidate_link_list),"normal")
                result[TEL_ID]["next_route"]["abnormal"] = self.calculate_TEL_senario(copy.deepcopy(candidate_link_list),"abnormal")
            #abnormal以下はabnormalだけ
            else:
                result[TEL_ID]["next_route"]["abnormal"] = self.calculate_TEL_senario(candidate_link_list,"abnormal")
            return result
            
    #メモ化による計算時間の短縮は可能かもしれない
    #選ばれたテレメトリの状態で残るリンクを探す？計算する
    def find_remain_link(self,result,candidate_link_list,TEL_result):
        #print(candidate_link_list)
        #次に返す時にpopする．dequeのほうが速いらしい
        pair, route = candidate_link_list.pop(0)
        TEL_ID = pair[1]
        #結果が正常の場合は経路内のものはすべて検証できたとする．今回は（複数故障を考えていないので）
        if TEL_result=="normal":
            #これCOMとTEL単純に足しちゃうと混ざるので辞書ごとコピー
            # 付け足していきたい．最終的に確認できたものが分かればいい　 
            result[TEL_ID]["normal_link"] ={"COM": route.copy()["COM"],"TEL":route.copy()["TEL"]}
            result[TEL_ID]["remain_link"] =  {"COM":[],"TEL":[]}#一応
            result[TEL_ID]["abnormal_link"] = {"COM":[],"TEL":[]}
            #他の経路から正常なものを除く
            for other_pair, other_route in candidate_link_list:
                #これで元も変更されるのか注意
                other_route["COM"] = list(set(other_route["COM"]) - set(route["COM"]))
                other_route["TEL"] = list(set(other_route["TEL"]) - set(route["TEL"]))
                #ない奴は消す
                if not other_route["COM"] and not other_route["TEL"]:
                    candidate_link_list.remove((other_pair, other_route))
            #print("normal",candidate_link_list)
        # このremain linkではこの経路内の話しかしていない．
        # これを提示する意味はある？他の経路に含まれるものも提示するほうがいいのか？

        #結果が異常の時はその時の確率に基づいて考える．
        #一つしかないときはそれが異常
        else:
            #確認確率が1なものはabnormal確定する
            if route["P_route"]["average"]==1:
                result[TEL_ID]["abnormal_link"] ={"COM":route["COM"],"TEL":[]}  if route["COM"] else {"COM":[],"TEL":route["TEL"]}
                result[TEL_ID]["remain_link"] = {"COM":[],"TEL":[]} #一応
                result[TEL_ID]["normal_link"] = {"COM":[],"TEL":[]}
                #この時点で終了となる．一つ異常が見つかれば終わりとしているため，空を返す
                # 複数の故障を扱えるようにする際にはよう変更点
                #ここで代入を使うと別参照になる．代入せずに消す．
                #print()
                candidate_link_list.clear()
            #複数存在するときもabnormalしか，以降許さないようにしている
            else:
                result[TEL_ID]["normal_link"] = {"COM":[],"TEL":[]}
                result[TEL_ID]["abnormal_link"] = {"COM":[],"TEL":[]}
                result[TEL_ID]["remain_link"] = {"COM": route.copy()["COM"],"TEL":route.copy()["TEL"]}
                #特に変更なし
            #print("abnormal",candidate_link_list)

    
    #残るリンクが計算されたら，次のコマンドの探索に入る．この時にsystemの関数が必要
    #探索はやらなくてよくて，あくまでもテレメトリの状態による場合分けとその確率を計算するまでにする．


    

