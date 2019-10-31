import sys, time, os
import pygame
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import cv2
import numpy as np
import math
from pygame.locals import *
import re
NULL,WIN,LOSE,DRAW = -1, 0, 1, 2 #左側のプレイヤーの勝敗状況に使う
class AirHockeyGame():
    #パソコンの画面によって画面サイズを変更する必要がある
    SCR_WIDTH,SCR_HEIGHT = 1280,720
    SCR_RECT = Rect(0, 0, 1280,720)
    def __init__(self):
        pygame.init() # pygame を起動
        self.screen = pygame.display.set_mode((self.SCR_WIDTH,self.SCR_HEIGHT))
        pygame.display.set_caption(u"画像認識エアホッケー")
        # 各種座標、速度の初期化
        self.timerMax = 0 #ホッケーゲームの制限時間
        self.pNumMax = 9 #設定できる最大のパックの数
        self.pNum = 1 #ゲーム内で遊ぶパックの数
        self.scoreMax = 0 #勝つのに必要な得点 
        #マレットのm
        self.mCursorX = [0.0] * 4 #カメラで読み込んだ位置x(瞬間移動あり)
        self.mCursorY = [0.0] * 4 #カメラで読み込んだ位置y(瞬間移動あり)
        self.mX = [0.0] * 4 #ゲーム上の位置x(瞬間移動なし)
        self.mY = [0.0] * 4 #ゲーム上の位置y(瞬間移動なし)
        self.mRadius = [30.0] * 4 #マレットの半径
        self.mColor = [[255,255,0],[255,0,0],[234,145,152],[153,204,255]] #マレットを描くときの色(赤黄ピンク水の順番)
          
        self.gameInit()
        self.isGameFinished = True #初めはゲーム開始しない
        self.clock = pygame.time.Clock()
        self.mouseX = self.mouseY = 0
        self.fullscreen_flag = False
        self.jpfont30 = pygame.font.Font("ipag.ttf",30)
        self.jpfont150 = pygame.font.Font("ipag.ttf",150)
        self.easyMode = True #パックにマレットを当てた時に必ず相手の方向に打てるようになるオプション
        self.isExplain = True #Trueの時に操作説明を表示する
        # fps計測スタート時間
        fpsCalculateStart = time.time()
        # fps計測終了時間
        fpsCalculateEnd = time.time()

    def gameInit(self):
        self.timer = 0 #ゲーム開始から何フレーム経ったかをカウント
        #パックのp    
        self.pX = [100.0] * self.pNumMax #パックの位置x
        self.pY = [-1000.0] * self.pNumMax #パックの位置y(最初は画面外に出す)
        self.pX[0] = self.SCR_WIDTH/2.0
        self.pY[0] = self.SCR_HEIGHT/2.0
        self.pSpeedX = [0.0] * self.pNumMax #速度をx方向に分解
        self.pSpeedY = [0.0] * self.pNumMax #速度をy方向に分解
        self.pSpeed = [0.0] * self.pNumMax #x方向とy方向の速度を足し合わせた速度
        self.pMaxSpeed = [40,30,30,20,20,20,20,20,20] #パックの最大速度
        self.pCollideVectorPi = 0.0 #パックとマレットが衝突し、パックをどの方向に飛ばすか計算するときに使う
        self.pCollideCount = [0] * self.pNumMax #パックがマレットに当たってから何フレーム経ったかをカウント
        self.pRadius = [40,30,30,20,20,20,20,20,20] #パックの半径
        self.pScore = [4,3,3,2,2,2,2,2,2] #パックを相手側にいれたときのスコア

        self.leftScore = 0 #右側のチームの点数
        self.rightScore = 0 #左側のチームの点数
        self.isGameFinished = False #勝敗が決定しているならTrue
        self.leftPlayersResult = NULL #左側のプレイヤーの勝敗状況

    def eventGet(self):
        continueflag = True
        for event in pygame.event.get():
            if event.type == QUIT: 
                pygame.quit()
                return False
            if event.type == KEYDOWN and event.key == K_ESCAPE: 
                pygame.quit()
                return False
            # マウスを移動させたときマレットを移動させる(デバッグ用)
            if event.type == MOUSEMOTION:
                mouseX,mouseY=event.pos
                #self.mCursorX[0], self.mCursorY[0] = mouseX,mouseY #デバッグ用                      
            if event.type == KEYDOWN and event.key == K_1:
                # 1キーでフルスクリーンモードへの切り替え
                self.fullscreen_flag = not self.fullscreen_flag
                if self.fullscreen_flag:
                    self.screen = pygame.display.set_mode(self.SCR_RECT.size, FULLSCREEN, 32)
                else:
                    self.screen = pygame.display.set_mode(self.SCR_RECT.size, 0, 32)   
            # 2,3キーでパックの数を切り替え
            if event.type == KEYDOWN and event.key == K_2:
                self.pNum = max(1,self.pNum-1)
            if event.type == KEYDOWN and event.key == K_3:
                self.pNum = min(self.pNumMax,self.pNum+1)
            # 4,5キーで必要得点を切り替え
            if event.type == KEYDOWN and event.key == K_4:
                self.scoreMax = max(0,self.scoreMax-1)
            if event.type == KEYDOWN and event.key == K_5:
                self.scoreMax = min(100,self.scoreMax+1)
            if event.type == KEYDOWN and event.key == K_F4:
                self.scoreMax = max(0,self.scoreMax-10)
            if event.type == KEYDOWN and event.key == K_F5:
                self.scoreMax = min(100,self.scoreMax+10)
            # 6,7キーで制限時間を切り替え            
            if event.type == KEYDOWN and event.key == K_6:
                self.timerMax = max(0,self.timerMax-100)
            if event.type == KEYDOWN and event.key == K_7:
                self.timerMax = min(10000,self.timerMax+100)
            if event.type == KEYDOWN and event.key == K_F6:
                self.timerMax = max(0,self.timerMax-1000)
            if event.type == KEYDOWN and event.key == K_F7:
                self.timerMax = min(10000,self.timerMax+1000)

            if event.type == KEYDOWN and event.key == K_SPACE:
                self.isExplain = not(self.isExplain) #TrueとFalseを反転
            if event.type == KEYDOWN and event.key == K_RETURN: #Enter
                self.gameInit()

        return continueflag
        
    def calcPrameter(self):
        if self.timerMax - self.timer >= 1 and self.isGameFinished == False:
            self.timer += 1
        if self.timerMax - self.timer <= 0:
            self.timer = self.timerMax
        if self.timer == 50:
            tmp = max(self.pNum,1)
            tmp = min(tmp,3)
            for i in range(1, tmp, 1):  
                self.pX[i] = self.SCR_WIDTH/2 + i * 20 - 30
                self.pY[i] = self.SCR_HEIGHT/2
                self.pSpeedY[i] = 0
            self.pSpeedX[1] = 5
            self.pSpeedX[2] = -5
        if self.timer == 100:
            tmp = max(self.pNum,3)
            for i in range(3, self.pNum, 1):  
                self.pX[i] = self.SCR_WIDTH/2 + i * 1 - 5.5
                self.pY[i] = self.SCR_HEIGHT/2
                if i <= 5:
                    self.pSpeedX[i] = -5
                else:
                    self.pSpeedX[i] = 5
            self.pSpeedY[3] = 5
            self.pSpeedY[4] = 0
            self.pSpeedY[5] = -5
            self.pSpeedY[6] = 5
            self.pSpeedY[7] = 0
            self.pSpeedY[8] = -5
        # 色検出(黄色)
        detector.detectYellow(viewer.Image)
        rect = detector.getCentersOfRects()
        if(len(rect) == 1): # 黄色の物体を検出した場合
            tmpX,tmpY = rect[0]
            self.mCursorX[0], self.mCursorY[0] = -2 * tmpX + 1280,tmpY * 2 - 120 #カメラの画像とウィンドウサイズが異なるので調整
             
        # 色検出(赤色)
        detector.detectRed(viewer.Image)
        rect = detector.getCentersOfRects()
        if(len(rect) == 1): # 赤い物体を検出した場合
            tmpX,tmpY = rect[0]
            self.mCursorX[1], self.mCursorY[1] = -2 * tmpX + 1280,tmpY * 2 - 120 #カメラの画像とウィンドウサイズが異なるので調整
        
        # 色検出(ピンク色)
        detector.detectPink(viewer.Image)
        rect = detector.getCentersOfRects()
        if(len(rect) == 1): # ピンク色の物体を検出した場合
            tmpX,tmpY = rect[0]
            self.mCursorX[2], self.mCursorY[2] = -2 * tmpX + 1280,tmpY * 2 - 120 #カメラの画像とウィンドウサイズが異なるので調整
        
        # 色検出(水色)
        detector.detectLightBlue(viewer.Image)
        rect = detector.getCentersOfRects()
        if(len(rect) == 1): # 水色の物体を検出した場合
            tmpX,tmpY = rect[0]
            self.mCursorX[3], self.mCursorY[3] = -2 * tmpX + 1280,tmpY * 2 - 120 #カメラの画像とウィンドウサイズが異なるので調整
        
        for i in range(0, 4, 1):    
            #全てのマレットとパックの衝突処理
            for j in range(0, self.pNum, 1):
                #if文を改行するために末尾に\を付けている
                if (self.mX[i] - self.pX[j]) ** 2 + (self.mY[i]-self.pY[j]) ** 2 < (self.mRadius[i] + self.pRadius[j]) ** 2 \
                and self.pCollideCount[j] > 2:
                    #マレットからパックの方向へのラジアンを計算
                    self.pCollideVectorPi = math.atan2(-self.mY[i] + self.pY[j],-self.mX[i] + self.pX[j])
                    self.pSpeed[j] = self.pMaxSpeed[j]
                    self.pSpeedX[j] = math.cos(self.pCollideVectorPi) * self.pSpeed[j]
                    if self.easyMode and ((0 <= i <= 1 and self.pSpeedX[j] < 0) or (2 <= i <= 3 and self.pSpeedX[j] > 0)):
                        self.pSpeedX[j] *= -1
                    self.pSpeedY[j] = math.sin(self.pCollideVectorPi) * self.pSpeed[j]
                    self.pCollideCount[j] = 0
                    self.pMaxSpeed[i] += 3
                    
            #全てのマレットの移動処理
            if (self.mCursorX[i] - self.mX[i]) ** 2 + (self.mCursorY[i] - self.mY[i]) ** 2 < (self.mRadius[i] * 2) ** 2:
                self.mX[i] = self.mCursorX[i]
                self.mY[i] = self.mCursorY[i]
            else: #全てのマレットの瞬間移動防止(1フレームにマレットの直径距離までしか動かせない)
                tmpPi = math.atan2(self.mCursorY[i] - self.mY[i],self.mCursorX[i] - self.mX[i])
                self.mX[i] += math.cos(tmpPi) * self.mRadius[i] * 2
                self.mY[i] += math.sin(tmpPi) * self.mRadius[i] * 2
                
        #全てのパックの壁衝突処理
        for i in range(0, self.pNum, 1):
            self.pSpeedX[i] *= 0.99
            self.pSpeedY[i] *= 0.99
            self.pX[i] += self.pSpeedX[i]
            self.pY[i] += self.pSpeedY[i]
            self.pCollideCount[i] += 1
            #x軸方向の画面外に完全にパックが出たら得点計算とパックを自分のコートに戻す
            if self.pX[i] < 0 - self.pRadius[i]: #左端と言うことを示すため、0 - self.pRadius[i]と書いている
                self.pX[i] = self.SCR_WIDTH * 3/8 - i * 30
                self.pY[i] = -50
                self.pSpeedX[i] = 0
                self.pSpeedY[i] = self.pRadius[i]
                self.pMaxSpeed[i] = self.pRadius[i]
                if self.isGameFinished == False:
                    self.rightScore += self.pScore[i]
            elif self.pX[i] > self.SCR_WIDTH + self.pRadius[i]:
                self.pX[i] = self.SCR_WIDTH * 5/8 + i * 30
                self.pY[i] = -50
                self.pSpeedX[i] = 0
                self.pSpeedY[i] = self.pRadius[i]
                if self.isGameFinished == False:
                    self.leftScore += self.pScore[i]
                
            #全てのパックがy軸方向の画面外に少しも出ないようにする処理
            if self.pY[i] < 0 + self.pRadius[i] and self.pSpeedY[i] < 0:
                self.pY[i] = 0 + self.pRadius[i]
                self.pSpeedY[i] *= -1
            elif self.pY[i] > self.SCR_HEIGHT - self.pRadius[i] and self.pSpeedY[i] > 0:
                self.pY[i] = self.SCR_HEIGHT - self.pRadius[i]
                self.pSpeedY[i] *= -1
        
        #全てのマレットが画面外に少しも出ないようにする処理
        for i in range(0, 4, 1):
            if self.mX[i] < 0 + self.mRadius[i]:
                self.mX[i] = 0 + self.mRadius[i]
            elif self.mX[i] > self.SCR_WIDTH - self.mRadius[i]:
                self.mX[i] = self.SCR_WIDTH - self.mRadius[i]
            if self.mY[i] < 0 + self.mRadius[i]:
                self.mY[i] = 0 + self.mRadius[i]
            elif self.mY[i] > self.SCR_HEIGHT - self.mRadius[i]:
                self.mY[i] = self.SCR_HEIGHT - self.mRadius[i]
            #相手のコートに自分のマレットが行かないようにする
            if 0 <= i <= 1 and self.mX[i] > self.SCR_WIDTH/2 - self.mRadius[i]:
                self.mX[i] = self.SCR_WIDTH/2 - self.mRadius[i]
            elif 2 <= i <= 3 and self.mX[i] < self.SCR_WIDTH/2 + self.mRadius[i]:
                self.mX[i] = self.SCR_WIDTH/2 + self.mRadius[i]

        #ゲームの勝敗判定
        if self.isGameFinished == False:
            if self.scoreMax <= self.leftScore and self.scoreMax != 0:
                self.leftPlayersResult = WIN
                self.isGameFinished = True
            elif self.scoreMax <= self.rightScore and self.scoreMax != 0:
                self.leftPlayersResult = LOSE
                self.isGameFinished = True
            elif self.timerMax - self.timer <= 0 and self.timerMax != 0:
                if self.leftScore == self.rightScore:
                    self.leftPlayersResult = DRAW
                elif self.leftScore < self.rightScore:
                    self.leftPlayersResult = LOSE
                else:
                    self.leftPlayersResult = WIN
                self.isGameFinished = True
                
    def drawGameObj(self):
        #カメラ画像の描画のy座標を-120させているのはカメラ画像の640:480を1280:960にし、ウィンドウは1280:720なのでその調整
        #pygame.transform.flip(pyg_Image, 0, 1)により、x座標方向にカメラ画像を反転
        self.screen.blit(pygame.transform.scale(pygame.transform.flip(viewer.pyg_Image, 1, 0), (1280,960)), (0, -120))
        scoreImage = self.jpfont30.render(str(self.leftScore) + ":" + str(self.rightScore), True, (255,255,255))
        scoreImageWidth = scoreImage.get_width()
        timeImage = self.jpfont30.render(str(self.timerMax-self.timer), True, (255,255,255))
        timeImageWidth = timeImage.get_width()
        #tmpScreenはマレット・パックを半透明に描くためのスクリーン
        tmpScreen = pygame.Surface((self.SCR_WIDTH, self.SCR_HEIGHT))
        tmpScreen.fill((255,255,255)) #tmpScreenを全て白色で塗りつぶす
        tmpScreen.set_colorkey((255,255,255)) #白色に対して透過処理できるように設定
        tmpScreen.set_alpha(100) #どのくらい半透明にするか設定
        for i in range(0, 4, 1): #マレットの描画
            pygame.draw.circle(tmpScreen, self.mColor[i], (int(self.mX[i]),int(self.mY[i])), int(self.mRadius[i])) #マレットの半透明の円
            pygame.draw.circle(self.screen, (0,0,0), (int(self.mX[i]),int(self.mY[i])), int(self.mRadius[i]),3) #黒色の円
        for i in range(0, self.pNum, 1): #パックの描画
            pygame.draw.circle(tmpScreen, (0,0,0), (int(self.pX[i]),int(self.pY[i])), self.pRadius[i]) #パックの黒色半透明の円
            pygame.draw.circle(self.screen, (0,0,0), (int(self.pX[i]),int(self.pY[i])), int(self.pRadius[i]/2),1) #黒色の円
            pygame.draw.circle(self.screen, (0,0,0), (int(self.pX[i]),int(self.pY[i])), self.pRadius[i],4) #黒色の円
            pygame.draw.circle(self.screen, (255,255,255), (int(self.pX[i]),int(self.pY[i])), self.pRadius[i],2) #白色の円
        
        pygame.draw.rect(tmpScreen, (0,0,0), Rect(self.SCR_WIDTH/2 - scoreImageWidth/2-5,0,scoreImageWidth+10,35)) #得点の灰色の矩形
        pygame.draw.rect(tmpScreen, (0,0,0), Rect(self.SCR_WIDTH/2 - timeImageWidth/2-5,self.SCR_HEIGHT-35,timeImageWidth+10,self.SCR_HEIGHT)) #時間の灰色の矩形
        if self.isExplain == True:
            pygame.draw.rect(tmpScreen, (0,0,0), Rect(0,0,600,280)) #操作説明の灰色の矩形        
        
        if self.leftPlayersResult == DRAW:
            leftResultMessage = self.jpfont150.render("DRAW",True, (0,0,0))
            rightResultMessage = self.jpfont150.render("DRAW",True, (0,0,0))
        elif self.leftPlayersResult == WIN:
            leftResultMessage = self.jpfont150.render("WIN",True, (255,0,0))
            rightResultMessage = self.jpfont150.render("LOSE",True, (0,0,255))
        elif self.leftPlayersResult == LOSE:
            leftResultMessage = self.jpfont150.render("LOSE",True, (0,0,255))
            rightResultMessage = self.jpfont150.render("WIN",True, (255,0,0))
        if self.leftPlayersResult != NULL:
            self.screen.blit(leftResultMessage,(100,300))
            self.screen.blit(rightResultMessage,(100+self.SCR_WIDTH/2,300))

        self.screen.blit(tmpScreen, (0, 0)) #tmpScreenを描画する

        if self.isExplain == True:
            message = self.jpfont30.render("1で全画面表示",True, (255,255,255))
            self.screen.blit(message,(0,0))
            message = self.jpfont30.render("2,3でパックの数を調整:パックの数="+str(self.pNum),True, (255,255,255))
            self.screen.blit(message,(0,40))
            message = self.jpfont30.render("4,5,F4,F5で必要得点を調整:必要得点="+str(self.scoreMax),True, (255,255,255))
            self.screen.blit(message,(0,80))
            message = self.jpfont30.render("6,7,F6,F7で制限時間を調整:制限時間="+str(self.timerMax),True, (255,255,255))
            self.screen.blit(message,(0,120))
            message = self.jpfont30.render("Enterでゲームスタート",True, (255,255,255))
            self.screen.blit(message,(0,160))
            message = self.jpfont30.render("Spaceで操作説明の表示切替",True, (255,255,255))
            self.screen.blit(message,(0,200))
            message = self.jpfont30.render("Escでゲーム終了",True, (255,255,255))
            self.screen.blit(message,(0,240))
        self.screen.blit(scoreImage, (self.SCR_WIDTH/2 - scoreImageWidth/2, 0))
        self.screen.blit(timeImage, (self.SCR_WIDTH/2 - timeImageWidth/2, self.SCR_HEIGHT-30))        

    def gameProcess(self):
        self.calcPrameter()
        self.drawGameObj()
        pygame.display.update()

class ColorDetector(): # 色検出器
    def __init__(self):
        None
        
    def detectYellow(self, im):
        hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV_FULL) # RGB画像をHSV色空間で表現 hsv: [x, y,(0:h,1:s,2:v)]
        h = hsv[:, :, 0] # 色相 360段階(実際は3パラメータすべて0～256の数値になっている模様)
        s = hsv[:, :, 1] # 彩度 0～100%
        v = hsv[:, :, 2] # 明度 0～100%
        
        mask = np.zeros(h.shape, dtype = np.uint8) # 画像サイズのゼロ行列を作成(type: uint8)
        #mask[((h > 91) & (h < 115)) & (s > 187) & (v > 209)] = 255 # 黄色い部分だけが255それ以外が0の行列ができる -> mask: 白黒画像
        mask[((h > 17) & (h < 35)) & (s > 130) & (v > 180)] = 255 # 黄色い部分だけが255それ以外が0の行列ができる -> mask: 白黒画像        
        #mask[((h > 36) & (h < 43)) & (s > 128) & (v > 116)] = 255 # 黄色い部分だけが255それ以外が0の行列ができる -> mask: 白黒画像        
        mask[:,:320] = 0 # 左半分のみ識別
    
        _, contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # マスク(白黒画像)から塊(contours)を検出
        self.rects = []
        for contour in contours:
            approx = cv2.convexHull(contour) # 塊を包むような凸集合を形成
            rect = cv2.boundingRect(approx)  # 凸集合に外接する矩形を作成 array(x, y, w, h) <- boundingRect (x, y):矩形左上座標, w, h:矩形の幅, 矩形の高さ
            self.rects.append(np.array(rect))     # 配列rectsは(矩形情報x, y, w, hの配列)の配列
            
        if len(self.rects) > 0:
            self.rects = sorted(self.rects, key=lambda x:x[2] * x[3], reverse = True) # 配列rectsを矩形の面積が大きい順にソート
            self.rects = self.rects[:1] # 指定した色の物体で大きいもの1つだけを抽出
        return self.rects
    
    def detectRed(self, im):
        hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV_FULL) # RGB画像をHSV色空間で表現 hsv: [x, y,(0:h,1:s,2:v)]
        h = hsv[:, :, 0] # 色相 360段階(実際は3パラメータすべて0～256の数値になっている模様)
        s = hsv[:, :, 1] # 彩度 0～100%
        v = hsv[:, :, 2] # 明度 0～100%
        
        mask = np.zeros(h.shape, dtype = np.uint8) # 画像サイズのゼロ行列を作成(type: uint8)
        mask[(((h>0) & (h<11))|(h>245) & (h<256))& (s>128) & (v>156)] = 255 # 赤い部分だけが255それ以外が0の行列ができる -> mask: 白黒画像
        mask[:,:320] = 0 # 左半分のみ識別
    
        _, contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # マスク(白黒画像)から塊(contours)を検出
        self.rects = []
        for contour in contours:
            approx = cv2.convexHull(contour) # 塊を包むような凸集合を形成
            rect = cv2.boundingRect(approx)  # 凸集合に外接する矩形を作成 array(x, y, w, h) <- boundingRect (x, y):矩形左上座標, w, h:矩形の幅, 矩形の高さ
            self.rects.append(np.array(rect))     # 配列rectsは(矩形情報x, y, w, hの配列)の配列
            
        if len(self.rects) > 0:
            self.rects = sorted(self.rects, key=lambda x:x[2] * x[3], reverse = True) # 配列rectsを矩形の面積が大きい順にソート
            self.rects = self.rects[:1] # 指定した色の物体で大きいもの1つだけを抽出
        return self.rects
    
    def detectPink(self, im):
        hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV_FULL) # RGB画像をHSV色空間で表現 hsv: [x, y,(0:h,1:s,2:v)]
        h = hsv[:, :, 0] # 色相 360段階(実際は3パラメータすべて0～256の数値になっている模様)
        s = hsv[:, :, 1] # 彩度 0～100%
        v = hsv[:, :, 2] # 明度 0～100%
        
        mask = np.zeros(h.shape, dtype = np.uint8) # 画像サイズのゼロ行列を作成(type: uint8)
        mask[((h>213) & (h<241))& (s>80) & (v>200)] = 255 # ピンクの部分だけが255それ以外が0の行列ができる -> mask: 白黒画像
    
        _, contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # マスク(白黒画像)から塊(contours)を検出
        self.rects = []
        for contour in contours:
            approx = cv2.convexHull(contour) # 塊を包むような凸集合を形成
            rect = cv2.boundingRect(approx)  # 凸集合に外接する矩形を作成 array(x, y, w, h) <- boundingRect (x, y):矩形左上座標, w, h:矩形の幅, 矩形の高さ
            self.rects.append(np.array(rect))     # 配列rectsは(矩形情報x, y, w, hの配列)の配列
            
        if len(self.rects) > 0:
            self.rects = sorted(self.rects, key = lambda x:x[2] * x[3], reverse = True) # 配列rectsを矩形の面積が大きい順にソート
            self.rects = self.rects[:1] # 指定した色の物体で大きいもの1つだけを抽出
        return self.rects
    
    def detectLightBlue(self, im):
        hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV_FULL) # RGB画像をHSV色空間で表現 hsv: [x, y,(0:h,1:s,2:v)]
        h = hsv[:, :, 0] # 色相 360段階(実際は3パラメータすべて0～256の数値になっている模様)
        s = hsv[:, :, 1] # 彩度 0～100%
        v = hsv[:, :, 2] # 明度 0～100%
        
        mask = np.zeros(h.shape, dtype = np.uint8) # 画像サイズのゼロ行列を作成(type: uint8)
        mask[((h > 128) & (h < 149)) & (s > 64) & (v > 196)] = 255 # 水色の部分だけが255それ以外が0の行列ができる -> mask: 白黒画像
    
        _, contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # マスク(白黒画像)から塊(contours)を検出
        self.rects = []
        for contour in contours:
            approx = cv2.convexHull(contour) # 塊を包むような凸集合を形成
            rect = cv2.boundingRect(approx)  # 凸集合に外接する矩形を作成 array(x, y, w, h) <- boundingRect (x, y):矩形左上座標, w, h:矩形の幅, 矩形の高さ
            self.rects.append(np.array(rect))     # 配列rectsは(矩形情報x, y, w, hの配列)の配列
            
        if len(self.rects) > 0:
            self.rects = sorted(self.rects, key = lambda x:x[2] * x[3], reverse = True) # 配列rectsを矩形の面積が大きい順にソート
            self.rects = self.rects[:1] # 指定した色の物体で大きいもの1つだけを抽出
        return self.rects
    
    def getCentersOfRects(self): # 物体を囲む矩形の中心座標を返す(ゲーム用)
        centers = []
        for i in range(len(self.rects)):
            (x, y, w, h) = self.rects[i]
            center = np.array([x + (w/2), y + (h/2)])
            centers.append(np.array(center))
        return centers

class VideoCaptureView(QGraphicsView):
    """ ビデオキャプチャ """
    def __init__(self, parent = None):
        """ コンストラクタ（インスタンスが生成される時に呼び出される） """
        super(VideoCaptureView, self).__init__(parent)
        
        # 変数を初期化
        self.pixmap = None
        self.item = None
        self.rect_items = []
        
        # VideoCapture (カメラからの画像取り込み)を初期化
        self.capture = cv2.VideoCapture(0)

        if self.capture.isOpened() is False:
            raise IOError("failed in opening VideoCapture")
        
        # 描画キャンバスの初期化
        self.scene = QGraphicsScene()
        
        self.Image = self.setVideoImage()
        self.shape = self.Image.shape[1::-1]
        self.pyg_Image = pygame.image.frombuffer(self.Image.tostring(), self.shape, 'RGB')
        
        self.timer = QTimer() #QTimerはホッケーゲームとWebカメラを異なる時間毎に呼び出すために使う
        self.timer.timeout.connect(self.cameraProcess) #1ms経ったらcameraProcessを呼ぶ
        self.timer.start(1) #self.cameraProcessを1ms毎に1回呼び出す
        self.start = time.time() #cameraProcessがどのくらいの速度で実行されているか確認する(デバッグ用)

    def setVideoImage(self):
        """ ビデオの画像を取得して表示 """
        ret, cv_Image = self.capture.read()                # ビデオキャプチャデバイスから画像を取得
        if ret == False:
            print("Error!!")
            return
        cv_Image = cv2.cvtColor(cv_Image,cv2.COLOR_BGR2RGB)  # 色変換 BGR->RGB
        height, width, dim = cv_Image.shape        
        bytesPerLine = dim * width                       # 1行辺りのバイト数
        
        self.image = QImage(cv_Image.data, width, height, bytesPerLine, QImage.Format_RGB888)
        if self.pixmap == None:                          # 初回はQPixmap, QGraphicPixmapItemインスタンスを作成
            self.pixmap = QPixmap.fromImage(self.image)
            self.item = QGraphicsPixmapItem(self.pixmap)
            self.scene.addItem(self.item)                # キャンバスに配置
        else:
            self.pixmap.convertFromImage(self.image)     # ２回目以降はQImage, QPixmapを設定するだけ
            self.item.setPixmap(self.pixmap)
        
        return cv_Image
    
    def cameraProcess(self):
        self.timer.stop() #self.timer.start(1)というメソッドは、1ms毎にcameraProcessを繰り返し呼び出すので、連続して呼び出さないように止める
        #以下4行cameraProcessがどのくらいの速度で実行されているか確認する(デバッグ用)
        self.end = time.time()
        seconds = self.end - self.start
        #print("経過時間：{0}".format(seconds))            
        self.start = time.time()
        # 以下3行でカメラ画像を取得する
        self.Image = self.setVideoImage()
        self.shape = self.Image.shape[1::-1]
        self.pyg_Image = pygame.image.frombuffer(self.Image.tostring(), self.shape, 'RGB')
        self.timer.start(1) #cameraProcessを1ms秒後に呼び出す(0msにすると原因不明のバグ)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)
    detector = ColorDetector()
    viewer = VideoCaptureView()       # VideoCaptureView ウィジエットviewを作成
    # 以下3行で先にカメラ画像を取得する
    viewer.Image = viewer.setVideoImage()
    viewer.shape = viewer.Image.shape[1::-1]
    viewer.pyg_Image = pygame.image.frombuffer(viewer.Image.tostring(), viewer.shape, 'RGB')
    game = AirHockeyGame()
    clock = pygame.time.Clock() #ホッケーゲームのfpsに使う
    
    while game.eventGet():
        clock.tick(30)  # ホッケーゲームは30fpsを上限とするはずだったが、何故か10fps程度にしかならない
        game.gameProcess()
