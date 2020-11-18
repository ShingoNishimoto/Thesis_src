
#リンクへのアクセスはID
class Link:
    #named_tupleを受け取る
    def __init__(self, link):
        self.name = link.Link_name
        self.component = [link.Compo1,link.Compo2]
        self.ID = link.ID
        self.medium = link.Medium
        self.probability = link.Probability
        self.valid = 0 #検証済みかどうか
        self.verifyCOMnum = 0
        #print(self.ID,self.component)
        

#各コンポごとにインスタンス化
#コンポへのアクセスは名前？
class Component:
    def __init__(self, compo): #,state
        com_linkID = compo.Com_linkID
        tel_linkID = compo.Tel_linkID
        #各ポートを全てリストとして持つ
        if (type(com_linkID) == str):
            #数値として扱う
            self.COM_link = [int(i) for i in com_linkID.split(',')]
        else:
            self.COM_link = [com_linkID]
        if (type(tel_linkID) == str):
            self.TEL_link = [int(i) for i in tel_linkID.split(',')]
        else:
            self.TEL_link = [tel_linkID]
        self.name = compo.Component
        self.state = {}
        #電源状態等をまとめて表現
        self.Active = True
        self.PowerConsumption = 0 #[W]
        self.Heat = 0
        self.Function = {}
        
    #stateの一部を変更した辞書を受取り，stateに関係する要素の更新を行う
    #直接更新した方がいい気がするが，一応名前はそのままにしておく．変えるかも
    def update_state(self,state_dict):
        self.state = state_dict
        #statusがないものは飛ばす
        if not len(self.state):
            return 0
        #電源状態
        self.Active = self.state["Active"]
        #電力消費量
        self.PowerConsumption = self.state["PowerConsumption"]["value"]
        self.Heat = self.state["Heat"] #+ or 0 or -?
        self.Function = self.state["Function"]
        return 1#この情報をどこかで使いたい
        
    #def find_link(self, link_list):
        