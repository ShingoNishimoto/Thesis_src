import copy

#いるんか？クラス
#コマンドの探索が必要になった段階の第一候補コマンドを受け取る．
#探索の過程にsystemのメソッド使いたい．てことはsystem全体をコピーする必要があるのか？
class Process:
    #対象のコマンドインスタンスを受け取る．
    # この時にcandidateTELのインスタンスたちももらうか
    def __init__(self,COM,TELs,candidate,COMlinks,TELlinks):
        self.COM = copy.deepcopy(COM)
        self.TELs = TELs
        self.candidateLink = candidate
        self.COMlinks = COMlinks
        self.TELlinks = TELlinks
        self.result = {ID:{} for ID in self.TELs.keys()}
        #いるものだけを受け取ったほうがいい気がするが．．使うならdeepcoyかな

    #全体の流れを決める関数．名前は考える
    def Process_flow(self):
        self.devide_TEL_result(COM)


    #コマンドが持つ確認候補があるテレメトリの結果を場合分けする
    # これはテレメトリ一つ一つにしても意味ない感じがする．
    # 確認可能性の高いペアから見ていった木構造を作る．経路ごとの平均確率を使う
    def devide_TEL_result(self,COM):
        # candidateを確率高い順にソート
        candidate_list = sorted(self.candidateLink.items(), key=lambda x:x[1]["P_route"]["average"],reverse=True)

        self.result = self.calculate_tel_senario(candidate_list)

    #テレメトリの結果がそのシナリオの結果になるための確率を計算
    def calculate_tel_senario(self,candidate_list):
        result = {}
        pair, route = candidate_list.pop(0)
        result[pair[1]]["normal"] = {}
        result[pair[1]]["abnormal"] = {}
        #その経路の平均確認確率を代入
        result[pair[1]]["normal"]["probability"] = route["P_route"]["average"]
        result[pair[1]]["abnormal"]["probability"] = 1 - route["P_route"]["average"]

        if len(candidate_list)==1:
            result[pair[1]]["next TEL"] = {}
            return result
        else:
            result[pair[1]]["next TEL"] = self.calculate_tel_senario(candidate_list)
            return result
            

    #選ばれたテレメトリの状態で残るリンクを探す？計算する
    def find_remain_link(self,TEL_ID):
        #結果が正常の場合はすべて検証できたとする．今回は（複数故障を考えていないので）
        self.result[TEL_ID]["normal"]["normal_link"] = self.candidateLink[(self.COM.ID,TEL_ID)]["COM"] +\
            self.candidateLink[(self.COM.ID,TEL_ID)]["TEL"]
        self.result[TEL_ID]["normal"]["remain_link"] = [] #一応
        # この残りではこの経路内の話しかしていない．他にもあることはある．
        # それとの差別化は？

        #結果が異常の時はその時の確率に基づいて考える．
        #一つしかないときはそれが異常
        if 
        self.result["normal"]["abnormal_link"] = self.candidateLink[(self.COM.ID,TEL_ID)]["COM"] \
            if self.candidateLink[(self.COM.ID,TEL_ID)]["COM"] else self.candidateLink[(self.COM.ID,TEL_ID)]["TEL"]
        self.result[TEL_ID]["abnormal"]["remain_link"] = [] #一応
        #複数存在するときは
        else:


    
    #残るリンクが計算されたら，次のコマンドの探索に入る．この時にsystemの関数が必要
    #探索はやらなくてよくて，あくまでもテレメトリの状態による場合分けとその確率を計算するまでにする．


    

