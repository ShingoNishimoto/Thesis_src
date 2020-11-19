import copy
from collections import deque

#いるんか？クラス
#コマンドの探索が必要になった段階の第一候補コマンドを受け取る．
#探索の過程にsystemのメソッド使いたい．てことはsystem全体をコピーする必要があるのか？
class Process:
    #対象のコマンドインスタンスを受け取る．
    # この時にcandidateTELのインスタンスたちももらうか
    def __init__(self,COM,candidate,COMlinks,TELlinks):
        #要らん説
        #self.COM = copy.deepcopy(COM)
        #ここで受け取るものは(COM_ID,candidate_TEL_ID)のものだけにする
        self.candidateLink = {}
        for TEL_ID in COM.candidate_TEL_ID:
            #ここにcandidateに入ってるけど中身ないやついる説．
            if not candidate[(COM.ID,TEL_ID)]["COM"] and not candidate[(COM.ID,TEL_ID)]["TEL"]:
                continue
            self.candidateLink[(COM.ID,TEL_ID)] = candidate[(COM.ID,TEL_ID)]
            #print(candidate[(COM.ID,TEL_ID)])
        self.COMlinks = COMlinks
        self.TELlinks = TELlinks
        self.result = {}
        #いるものだけを受け取ったほうがいい気がするが．．使うならdeepcoyかな

    #コマンドが持つ確認候補があるテレメトリの結果を場合分けする
    # これはテレメトリ一つ一つにしても意味ない感じがする．
    # 確認可能性の高いペアから見ていった木構造を作る．経路ごとの平均確率を使う
    def Process_flow(self):
        # candidateを確率高い順にソート
        candidate_link_list = copy.deepcopy(sorted(self.candidateLink.items(), key=lambda x:x[1]["P_route"]["average"],reverse=True)) 
        #これコピー渡さんと他の結果に影響する
        self.result["normal"] = self.calculate_tel_senario(copy.deepcopy(candidate_link_list),"normal")
        self.result["abnormal"] = self.calculate_tel_senario(copy.deepcopy(candidate_link_list),"abnormal")
        #print("normal",self.result["normal"])
        #print("abnormal",self.result["abnormal"])


    #テレメトリの結果がそのシナリオの結果になるための確率を計算
    def calculate_tel_senario(self,candidate_link_list,Tel_result):
        result = {}
        #print(candidate_link_list)
        pair, route = candidate_link_list[0]
        TEL_ID = pair[1]
        result[TEL_ID] = {}
        #その経路で結果が正常or異常になる確率
        # averageの代入だけだと結果に応じた更新ができていない
        P_tel_normal = 1
        for COMlink in route["COM"]:
            P_tel_normal = P_tel_normal*self.COMlinks[COMlink].probability
        for TELlink in route["TEL"]:
            P_tel_normal = P_tel_normal*self.TELlinks[TELlink].probability
        
        #candidateがテレメの結果によって変わるはずなので引数に応じて分岐させるか．
        if Tel_result=="normal":
            result[TEL_ID]["probability"] = P_tel_normal
        else:
            result[TEL_ID]["probability"] = 1 - P_tel_normal

        #print("before",candidate_link_list)
        self.find_remain_link(result,candidate_link_list,Tel_result)
        #print("after",candidate_link_list)
        #print(result[TEL_ID])

        #最後の経路.popしているので空
        #結果がnormal, abnormal関係なく次に見るテレメトリは決まるのか？
        result[TEL_ID]["next route"] = {}
        if not candidate_link_list:
            return result
        else:
            #candidate_link_listを更新
            if Tel_result=="normal":
                result[TEL_ID]["next route"]["normal"] = self.calculate_tel_senario(copy.deepcopy(candidate_link_list),"normal")
                result[TEL_ID]["next route"]["abnormal"] = self.calculate_tel_senario(copy.deepcopy(candidate_link_list),"abnormal")
            #abnormal以下はabnormalだけ
            else:
                result[TEL_ID]["next route"]["abnormal"] = self.calculate_tel_senario(candidate_link_list,"abnormal")
            return result
            
    #選ばれたテレメトリの状態で残るリンクを探す？計算する
    def find_remain_link(self,result,candidate_link_list,TEL_result):
        print(candidate_link_list)
        #次に返す時にpopする．dequeのほうが速いらしい
        pair, route = candidate_link_list.pop(0)
        TEL_ID = pair[1]
        #結果が正常の場合は経路内のものはすべて検証できたとする．今回は（複数故障を考えていないので）
        if TEL_result=="normal":
            #これCOMとTEL単純に足しちゃうと混ざるので辞書ごとコピー
            result[TEL_ID]["normal_link"] ={"COM": route.copy()["COM"],"TEL":route.copy()["TEL"]}
            result[TEL_ID]["remain_link"] = [] #一応
            result[TEL_ID]["abnormal_link"] = []
            #他の経路から正常なものを除く
            for other_pair, other_route in candidate_link_list:
                #これで元も変更されるのか注意
                other_route["COM"] = list(set(other_route["COM"]) - set(route["COM"]))
                other_route["TEL"] = list(set(other_route["TEL"]) - set(route["TEL"]))
                #ない奴は消す
                if not other_route["COM"] and not other_route["TEL"]:
                    candidate_link_list.remove((other_pair, other_route))
            print("normal",candidate_link_list)
        # この残りではこの経路内の話しかしていない．他にもあることはある．
        # それとの差別化は？

        #結果が異常の時はその時の確率に基づいて考える．
        #一つしかないときはそれが異常
        else:
            #確認確率が1なものはabnormal確定する
            if route["P_route"]["average"]==1:
                result[TEL_ID]["abnormal_link"] = route["COM"] if route["COM"] else route["TEL"]
                result[TEL_ID]["remain_link"] = [] #一応
                result[TEL_ID]["normal_link"] = []
                #この時点で終了となる．一つ異常が見つかれば終わりとしているため，空を返す
                candidate_link_list = []
            #複数存在するときは
            else:
                result[TEL_ID]["normal_link"] = []
                result[TEL_ID]["abnormal_link"] = []
                result[TEL_ID]["remain_link"] = {"COM": route.copy()["COM"],"TEL":route.copy()["TEL"]}
                #特に変更なし
            print("abnormal",candidate_link_list)

    
    #残るリンクが計算されたら，次のコマンドの探索に入る．この時にsystemの関数が必要
    #探索はやらなくてよくて，あくまでもテレメトリの状態による場合分けとその確率を計算するまでにする．


    

