.. -*- coding: utf-8 -

LightPomodoro
=============================

Pomodoro en PyQt4.

Testé sous Linux/Ubuntu 11.04.
*Non testé sous Windows et autres*.

Préalable
=============================

sudo apt-get install python-qt
sudo apt-get install libnotify-bin

Si gnome : vérifier présence applet "notification area" pour voir l'icône de LightPomodoro s'afficher
Si kde : vérifier présence applet "Boîte à miniatures" pour voir l'icône de LightPomodoro s'afficher

Lancement
==============================

python -u "lightpomodoro.pyw" &

Lancement automatique au démarrage
==============================

Kde:

    - Menu KDE
    - Configuration du Système 
    - Démarrage & Arrêt 
    - Démarrage Automatique 
    - Ajouter un programme : python -u "PATHTO/lightpomodoro.pyw"
    - Ok

Gnome:

    - Menu Gnome
    - System
    - Preference
    - Startup Applications
    - Add : python -u "PATHTO/lightpomodoro.pyw"
    - Ok

Usage 
==============================

- click gauche : start/pause
- click milieu : stop
- click droit : menu

Le temps restant est indiqué dans le tooltip quand on survole à la souris l'icone de l'application.
Il est aussi possible de consulter le temps restant dans la console via le fichier /tmp/lightpomodoro sous Linux ou en passant l'argument `tps` : `python -u "lightpomodoro.pyw" tps`



