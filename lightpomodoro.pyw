#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licence : GPL

"""
LightPomodoro - petit applet en pyqt4
avec 25 minutes de travail suivi de 5 minutes de break

installation & usage : lire le fichier README.rst
"""

__author__ = "Alban Minassian"
__copyright__ = "Copyright (c) 2011, Alban Minassian"
__date__ = "2011/09/30"
__version__ = "0.1"

import tempfile
import datetime
import sys, os, platform
from PyQt4 import QtCore, QtGui
import icons_rc # pyrcc4 icons.qrc -o icons_rc.py

from PyQt4.QtNetwork import *
import thread,socket

# fichier de consultation du temps restant
fileTempsRestant = os.path.join(tempfile.gettempdir(), 'lightpomodoro')

class LightPomodoroDialog( QtGui.QDialog ):
    """
    Fenêtre de configuration
    """    
    def __init__(self, parent=None):  
        super(LightPomodoroDialog, self).__init__(parent)
        
        self.setWindowIcon(QtGui.QIcon(':/Ressources/working.png'))
        self.setWindowTitle("LightPomodoro")

class LightPomodoroSystray(QtGui.QWidget):
    """
    LightPomodoro 
    """    
    
    # (faux) enum des états
    WORK = 0
    PAUSE = 1
    STOP = 2
    BREAK = 3
    
    #~ # interval pomodoro
    INTERVAL_WORK = 25 * 60 * 1000 # 25 minutes
    INTERVAL_BREAK_SHORT = 5 * 60 * 1000 # 5 minutes
    INTERVAL_BREAK_LONG = 15 * 60 * 1000 # 15 minutes

    #~ # durée Test :
    #~ INTERVAL_WORK = 2 * 1000 # 2 secondes
    #~ INTERVAL_BREAK_SHORT = 2 * 1000 # 2 secondes
    #~ INTERVAL_BREAK_LONG = 5 * 1000 # 5 secondes
    
    # Compter le nombre de break
    # au bout de X break court alors réaliser un break long
    longBreakAfterXShort = 3 # long break after 3 short break
    countBreakShort = 0
    
    # Chaine info
    stringTempRestant = ''; # mis à jour toutes les X secondes via fncTempsRestant
    
    
    def __init__(self, argDialog):
        """
        Systray & Actions
        """    
        QtGui.QWidget.__init__(self)
        
        # sauvegarder pointeur sur la fenêtre de dialogue
        self.dialog = argDialog; 
        
        # icone
        #~ self.iconStop = QtGui.QIcon("idle.png")
        #~ self.iconStart = QtGui.QIcon("working.png")
        #~ self.iconPause = QtGui.QIcon("pause.png")
        #~ self.iconEnd = QtGui.QIcon("ok.png")
        
        self.iconStop = QtGui.QIcon(":/Ressources/idle.png")
        self.iconStart = QtGui.QIcon(":/Ressources/working.png")
        self.iconPause = QtGui.QIcon(":/Ressources/pause.png")
        self.iconEnd = QtGui.QIcon(":/Ressources/ok.png")
        
        # timer pomodoro en mode travail intensif  (25 minutes)
        self.timerPomodoroWork = QtCore.QTimer();
        self.timerPomodoroWork.setSingleShot(True); # important sinon redémarre dès la fin de son cycle
        QtCore.QObject.connect(self.timerPomodoroWork, QtCore.SIGNAL("timeout()"), self.fncEndWork )
        
        # timer pomodoro en mode break (5minutes ou plus si déjà 3 à 4 pauses)
        self.timerPomodoroBreak = QtCore.QTimer();
        self.timerPomodoroBreak.setSingleShot(True); # important sinon redémarre dès la fin de son cycle
        QtCore.QObject.connect(self.timerPomodoroBreak, QtCore.SIGNAL("timeout()"), self.fncEndBreak )
        
        # timer pour mettre à jour info temps restant
        self.timerSeconde = QtCore.QTimer();
        QtCore.QObject.connect(self.timerSeconde, QtCore.SIGNAL("timeout()"), self.fncUpdateSystray )
        self.timerSeconde.start(1000) ; # appelle fncTempsRestant() toutes les secondes
        
        # temps ecoulé pour calculer temp restant de travail ou de pause
        self.tempsEcoule = QtCore.QTime() # sans (r)
        
        # initialiser trayIcon
        self.trayIcon = QtGui.QSystemTrayIcon(self.iconStop, self)
        self.trayIcon.setToolTip(self.tr("LightPomodoro"))
        QtCore.QObject.connect(self.trayIcon, QtCore.SIGNAL("activated(QSystemTrayIcon::ActivationReason)"), self.fncSystrayClick )
        self.trayIcon.show()
        
        # créer l'action : quitter 
        self.actionQuit = QtGui.QAction(self.tr("Quit"), self)
        #~ QtCore.QObject.connect(self.actionQuit, QtCore.SIGNAL("triggered()"),	QtGui.qApp, QtCore.SLOT("quit()"))
        QtCore.QObject.connect(self.actionQuit, QtCore.SIGNAL("triggered()"),	self.fncQuit )
        # créer l'action : afficher fenêtre de dialogue
        self.actionShowDialog = QtGui.QAction(self.tr("Dialog"), self)
        QtCore.QObject.connect(self.actionShowDialog, QtCore.SIGNAL("triggered()"), self.fncShowDialog )
        # créer l'action : about
        self.actionShowAbout = QtGui.QAction(self.tr("A propos"), self)
        QtCore.QObject.connect(self.actionShowAbout, QtCore.SIGNAL("triggered()"), self.fncShowAbout )
        # créer l'action : start
        self.actionStart = QtGui.QAction(self.tr("Start"), self)
        self.actionStart.setIcon(self.iconStart)
        QtCore.QObject.connect(self.actionStart, QtCore.SIGNAL("triggered()"), self.fncWork )
        # créer l'action : end
        self.actionEnd = QtGui.QAction(self.tr("End"), self)
        self.actionEnd.setIcon(self.iconEnd)
        QtCore.QObject.connect(self.actionEnd, QtCore.SIGNAL("triggered()"), self.fncEndWork )
        # créer l'action : pause
        self.actionPause = QtGui.QAction(self.tr("Pause"), self)
        self.actionPause.setIcon(self.iconPause)
        QtCore.QObject.connect(self.actionPause, QtCore.SIGNAL("triggered()"), self.fncPause )
        # créer l'action : stop
        self.actionStop = QtGui.QAction(self.tr("Stop"), self)
        self.actionStop.setIcon(self.iconStop)
        QtCore.QObject.connect(self.actionStop, QtCore.SIGNAL("triggered()"), self.fncStop )
        # ajouter les actions dans un menu qui sera associé au systray
        self.menuTrayIcon = QtGui.QMenu(self)
        self.menuTrayIcon.setTitle (self.tr("LightPomodoro"))
        self.menuTrayIcon.addAction(self.actionQuit)
        #~ self.menuTrayIcon.addAction(self.actionShowDialog)
        self.menuTrayIcon.addAction(self.actionShowAbout)
        self.menuTrayIcon.addSeparator ()
        self.menuTrayIcon.addAction(self.actionStart)
        self.menuTrayIcon.addAction(self.actionPause)
        self.menuTrayIcon.addAction(self.actionStop)
        # associer menu au trayIcon
        self.trayIcon.setContextMenu(self.menuTrayIcon)
        
        # démarrer à l'état Stop
        self.fncStop(False) # argShowMessage=False car au démarrage de GNOME ou Kde, le statutMessage est affiché en haut à gauche de l'écran
        
        # info utilisateur
        if platform.system() == 'Linux' : 
            print """consulter temps restant en mode console : cat "%s" """  % fileTempsRestant
        else :
            print """consulter temps restant en mode console : type "%s" | more """  % fileTempsRestant
            
    
    def fncQuit(self):
        """
        
        """    
        result = QtGui.QMessageBox.question(self, self.tr('Confirmer'), self.tr('Quitter LightPomodoro ?'), QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes :
            self.fncStop(False) # argShowMessage=False, ( et mise à jour du fichier fileTempsRestant )            
            QtGui.qApp.quit()

    def fncShowDialog(self):
        """
        Afficher la fenêtre de configuration
        """    
        self.dialog.show()

    def fncShowAbout(self):
        """
        Afficher la fenêtre a propos
        """    
        result = QtGui.QMessageBox.about(None, self.tr("LightPomodoro"), self.tr("""LightPomodoro - petit applet en pyqt4 avec 25 minutes de travail suivi de 5 minutes de break"""))

    def fncSystrayClick(self, argActivationReason):
        """
        Selon click sur le systray
        """    
        
        if argActivationReason == QtGui.QSystemTrayIcon.DoubleClick :# The system tray entry was double clicked
            pass
        elif argActivationReason == QtGui.QSystemTrayIcon.Trigger : # The system tray entry was clicked
            if self.statut == self.WORK : 
                self.fncPause()
            elif self.statut == self.BREAK : 
                self.fncStop()
            else :
                self.fncWork()
        elif argActivationReason == QtGui.QSystemTrayIcon.MiddleClick : # The system tray entry was clicked with the middle mouse button
            self.fncStop()
            
            
    def fncWork(self):
        """
        Démarrer timer selon un interval tenant compte de l'action pause 
        """    
        
        # selon état précédent, réinitialiser temps interval
        if self.statut == self.PAUSE : 
            pass # self.tempsRestant = self.tempsRestant;
        else :
            self.tempsRestant = self.INTERVAL_WORK;
            self.tempsEcoule.restart(); # réinitialiser le temps ecoulé pour gérer le temps restant suite à une pause et pour calculer temps restant du break
            
        # démarrer le timer
        self.statut = self.WORK; 
        self.statutMessage = self.tr('Work')
        self.timerPomodoroWork.start(self.tempsRestant) ;# appelle fncEndWork() après ces 25 minutes de travail
        
        # activer l'action pause et désactiver l'action start
        self.actionStart.setEnabled(False)
        self.actionPause.setEnabled(True)
        self.actionStop.setEnabled(True)
        
        # affichage
        self.trayIcon.setIcon(self.iconStart)
        self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage)
        self.trayIcon.showMessage (self.tr("LightPomodoro"), self.statutMessage, QtGui.QSystemTrayIcon.Information, 1000);
        self.fncUpdateSystray()

    def fncPause(self):
        """
        Pause du timer 
        l'absence de méthode pause() nécessite de calculer le temps restant 
        """    
        # mettre en pause
        self.statut = self.PAUSE; 
        self.statutMessage = self.tr('Pause')
        # self.timerPomodoroWork.pause() < -- n'existe pas, gérer le tempsRestant manuellement
        self.timerPomodoroWork.stop() 
        self.tempsRestant = self.timerPomodoroWork.interval() - self.tempsEcoule.elapsed();   
        if self.tempsRestant < 0 : self.tempsRestant = 0; 
        
        # désactiver l'action pause et activer l'action start
        self.actionStart.setEnabled(True)
        self.actionPause.setEnabled(False)
        self.actionStop.setEnabled(True)
        
        # affichage
        self.trayIcon.setIcon(self.iconPause)
        self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage)
        self.trayIcon.showMessage (self.tr("LightPomodoro"), self.statutMessage, QtGui.QSystemTrayIcon.Information, 2000);
        self.fncUpdateSystray()
        
    def fncStop(self, argShowMessage=True):
        """
        Stop du timer 
        """    
        
        # arrêter les timer
        self.statut = self.STOP; 
        self.statutMessage = self.tr('Stop')
        self.timerPomodoroWork.stop()
        self.timerPomodoroBreak.stop()
        
        # désactiver l'action pause, activer Start
        self.actionStart.setEnabled(True)
        self.actionPause.setEnabled(False)
        self.actionStop.setEnabled(False)
        
        # affichage
        self.trayIcon.setIcon(self.iconStop)
        self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage)
        if argShowMessage == True : # mis en place car au démarrage de kde ou Gnome, l'applet se trouve en haut à gauche de l'écran ... le temps que l'os le repositionne dans la barre du systray
            self.trayIcon.showMessage (self.tr("LightPomodoro"), self.statutMessage, QtGui.QSystemTrayIcon.Information, 3000);
        self.fncUpdateSystray()

    def fncEndWork(self):
        """
        Fin du temps pomodoro travail
        """    
        
        # stopper le timer de travail
        self.statut = self.BREAK;
        self.timerPomodoroWork.stop()
        
        # démarrer le le timer de break court ou long
        self.countBreakShort += 1;
        if self.countBreakShort <= self.longBreakAfterXShort : 
            self.tempsEcoule.restart(); # réinitialiser le temps ecoulé pour gérer le temps restant pour calculer temps restant du break
            self.timerPomodoroBreak.start(self.INTERVAL_BREAK_SHORT) ; # appelle fncEndBreak() après ces 5 minutes de pause
            self.statutMessage = self.tr('Break')
        else :
            self.tempsEcoule.restart(); # réinitialiser le temps ecoulé pour gérer le temps restant  pour calculer temps restant du break
            self.timerPomodoroBreak.start(self.INTERVAL_BREAK_LONG) ; # appelle fncEndBreak() après ces 15 minutes de pause
            self.statutMessage = self.tr('Break LONG ...')
            self.countBreakShort = 0; # réinitialiser
        
        # affichage
        self.trayIcon.setIcon(self.iconEnd)
        self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage)
        self.trayIcon.showMessage (self.tr("LightPomodoro"), self.statutMessage, QtGui.QSystemTrayIcon.Information, 3000);
        self.fncUpdateSystray()
        
        # lib-notify des break complémentaire
        if platform.system() == 'Linux' : 
            cmd = """notify-send -t 1000000 --urgency=critical --icon=/usr/share/pixmaps/apple-green.png "LightPomodoro" "%s" """%self.statutMessage
            os.system(cmd);

    def fncEndBreak(self):
        """
        Fin du temps pomodoro break
        """    
        
        # stopper le timer
        self.timerPomodoroBreak.stop()
        
        # stop
        self.fncStop(False); # argShowMessage=False

    def fncUpdateSystray(self):
        
        # mettre à jour le tooltip du systay
        tempRestant = self.fncTempsRestant()
        if tempRestant != None : 
            self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage+', temps restant : '+tempRestant )
            #~ QtGui.qApp.processEvents(); 
            #~ self.trayIcon.update(); 
            #~ QtGui.qApp.repaint(); 
            #~ self.trayIcon.repaint(); 
        else :
            self.trayIcon.setToolTip(self.tr("LightPomodoro, ")+self.statutMessage)
            
        # mettre à jour le fichier pour lecture depuis la console
        f = open(fileTempsRestant, 'w')
        if tempRestant != None : 
            f.write(tempRestant+', '+self.statutMessage+"\n")
        else :
            f.write(self.statutMessage+"\n")
        f.close()

    def fncTempsRestant(self):

        if self.statut == self.WORK : 
            tempsRestantMilliSeconde = self.timerPomodoroWork.interval() - self.tempsEcoule.elapsed();   
            if tempsRestantMilliSeconde < 0 : tempsRestantMilliSeconde = 0
            return self.fncFormatMilliseconds(tempsRestantMilliSeconde)
        elif self.statut == self.PAUSE : 
            return None
        elif self.statut == self.BREAK : 
            tempsRestantMilliSeconde = self.timerPomodoroBreak.interval() - self.tempsEcoule.elapsed();   
            if tempsRestantMilliSeconde < 0 : tempsRestantMilliSeconde = 0
            return self.fncFormatMilliseconds(tempsRestantMilliSeconde)
        elif self.statut == self.STOP : 
            return None
        else :
            return None

    def fncFormatMilliseconds(self, millis):
        """http://www.megasolutions.net/python/Formatting-milliseconds-to-certain-String-10885.aspx
        millis is an integer number of milliseconds. 
        Return str hh:mm:ss,ttt
        """
        seconds, millis = divmod(millis, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d" % (minutes, seconds)

if __name__ == "__main__":
    
    if len(sys.argv) == 2 and sys.argv[1] == 'tps' :
        """Afficher le temps restant 
        """
        if os.path.exists(fileTempsRestant) : 
            f = open(fileTempsRestant, 'r')
            print f.read().strip()
            f.close()
        else :
            print "démarrer lightpomodoro au préalable !"
        
    else :
        """Démarrer l'application
        """
        app = QtGui.QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False) # indispensable, True par défaut 
        dialog = LightPomodoroDialog()
        x = LightPomodoroSystray( dialog )
        sys.exit(app.exec_())		
    
