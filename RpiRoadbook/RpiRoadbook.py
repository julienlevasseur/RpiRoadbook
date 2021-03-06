#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 08:58:53 2018

@author: Hien TRAN-QUANG
"""

# Pour masquer le message de la version de pygame
#import contextlib
#with contextlib.redirect_stdout(None):
import pygame.display

# Pour l'affichage sur le framebuffer
from pygame.locals import *

import time
import os
import configparser
import re
import serial
# Pour la lecture des fichiers pdf et conversion en image
from pdf2image import page_count,convert_from_path,page_size
import subprocess

import RPi.GPIO as GPIO

distance = 0
speed = 0.00
roue = 186
vmax = 0.00
vmoy = 0.0
tps = 0.0
tpsinit=0.0
j = 0
cmavant = 0

BOUTON13 = USEREVENT+1 # Odometre
BOUTON16 = USEREVENT+2 # Bouton left (tout en haut)
BOUTON19 = USEREVENT+3 # Bouton right (tout en bas)
BOUTON20 = USEREVENT+4 # Bouton OK/select (au milieu)
BOUTON21 = USEREVENT+5 # Bouton Up (2eme en haut)
BOUTON26 = USEREVENT+6 # Bouton Down (2eme en bas)
GMASSSTORAGE = USEREVENT+7 # Event branchement en mode cle usb

GPIO.setmode(GPIO.BCM)
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Capteur de vitesse
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#*******************************************************************************************************#
#------------------------- Les callbacks des interruptions GPIO  ---------------------------------------#
#*******************************************************************************************************#
def input_13_callback(channel):
    global distance
    distance += roue

def input_16_callback(channel):
    pygame.event.post(pygame.event.Event(BOUTON16))

def input_19_callback(channel):
    pygame.event.post(pygame.event.Event(BOUTON19))

def input_20_callback(channel):
    pygame.event.post(pygame.event.Event(BOUTON20))

def input_21_callback(channel):
    pygame.event.post(pygame.event.Event(BOUTON21))

def input_26_callback(channel):
    pygame.event.post(pygame.event.Event(BOUTON26))

def g_mass_storage_callback(channel):
    pygame.event.post(pygame.event.Event(GMASSSTORAGE))

#On définit les interruptions sur les GPIO des commandes
GPIO.add_event_detect(13, GPIO.FALLING, callback=input_13_callback, bouncetime=20)
GPIO.add_event_detect(16, GPIO.FALLING, callback=input_16_callback, bouncetime=200)
GPIO.add_event_detect(19, GPIO.FALLING, callback=input_19_callback, bouncetime=200)
GPIO.add_event_detect(20, GPIO.FALLING, callback=input_20_callback, bouncetime=200)
GPIO.add_event_detect(21, GPIO.FALLING, callback=input_21_callback, bouncetime=200)
GPIO.add_event_detect(26, GPIO.FALLING, callback=input_26_callback, bouncetime=200)


#*******************************************************************************************************#
#---------------------------------------- Le template de classe / écran  -------------------------------#
#*******************************************************************************************************#
class SceneBase:
    def __init__(self, fname = ''):
        self.next = self
        self.filename = fname

    def ProcessInput(self, events, pressed_keys):
        print("uh-oh, you didn't override this in the child class")

    def Update(self):
        print("uh-oh, you didn't override this in the child class")

    def Render(self, screen):
        print("uh-oh, you didn't override this in the child class")

    def SwitchToScene(self, next_scene):
        self.next = next_scene

    def Terminate(self):
        self.SwitchToScene(None)

#*******************************************************************************************************#
#--------------------------------------- La boucle principale de l'appli -------------------------------#
#*******************************************************************************************************#
def run_RpiRoadbook(width, height, fps, starting_scene):
    pygame.display.init() ;
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((width, height))

    clock = pygame.time.Clock()

    active_scene = starting_scene

    while active_scene != None:
        pressed_keys = pygame.key.get_pressed()

        # Event filtering
        filtered_events = []
        for event in pygame.event.get():
            quit_attempt = False
            if event.type == pygame.QUIT:
                quit_attempt = True
            elif event.type == pygame.KEYDOWN:
                alt_pressed = pressed_keys[pygame.K_LALT] or \
                              pressed_keys[pygame.K_RALT]
                if event.key == pygame.K_ESCAPE:
                    quit_attempt = True
                elif event.key == pygame.K_F4 and alt_pressed:
                    quit_attempt = True

            if quit_attempt:
                active_scene.Terminate()
            else:
                filtered_events.append(event)

        active_scene.ProcessInput(filtered_events, pressed_keys)
        active_scene.Update()
        active_scene.Render(screen)

        active_scene = active_scene.next

        pygame.display.flip()
        clock.tick(fps)
    GPIO.cleanup()




#*******************************************************************************************************#
#---------------------------------------- Ecran de sélection du Roadbook -------------------------------#
#*******************************************************************************************************#
class TitleScene(SceneBase):
    def __init__(self):
        SceneBase.__init__(self)

        pygame.font.init()
        self.maconfig = configparser.ConfigParser()

	      # Vérification de l'existence du fichier de config
        try:
	        with open('RpiRoadbook.cfg'): pass
        except IOError:
            with open('RpiRoadbook.cfg', 'w') as configfile:
                self.maconfig['Parametres_Odometre']={}
                self.maconfig['Parametres_Odometre']['roue'] = '1860'
                self.maconfig['Parametres_Odometre']['nb_aimants'] = '1'
                self.maconfig['Parametres_Odometre']['totalisateur'] = '0'
                self.maconfig['Paysage']={}
                self.maconfig['Paysage']['l_tps_x'] = '10'
                self.maconfig['Paysage']['l_tps_y'] = '5'
                self.maconfig['Paysage']['l_km_x'] = '440'
                self.maconfig['Paysage']['l_km_y'] = '-10'
                self.maconfig['Paysage']['l_vi_x'] = '650'
                self.maconfig['Paysage']['l_vi_y'] = '150'
                self.maconfig['Paysage']['l_vm_x'] = '650'
                self.maconfig['Paysage']['l_vm_y'] = '350'
                self.maconfig['Paysage']['l_case1_x'] = '0'
                self.maconfig['Paysage']['l_case1_y'] = '100'
                self.maconfig['Paysage']['l_case2_x'] = '0'
                self.maconfig['Paysage']['l_case2_y'] = '300'
                self.maconfig['Portrait']={}
                self.maconfig['Portrait']['l_tps_x'] = '10'
                self.maconfig['Portrait']['l_tps_y'] = '5'
                self.maconfig['Portrait']['l_km_x'] = '440'
                self.maconfig['Portrait']['l_km_y'] = '-10'
                self.maconfig['Portrait']['l_vi_x'] = '650'
                self.maconfig['Portrait']['l_vi_y'] = '150'
                self.maconfig['Portrait']['l_vm_x'] = '650'
                self.maconfig['Portrait']['l_vm_y'] = '350'
                self.maconfig['Portrait']['l_case1_x'] = '0'
                self.maconfig['Portrait']['l_case1_y'] = '100'
                self.maconfig['Portrait']['l_case2_x'] = '0'
                self.maconfig['Portrait']['l_case2_y'] = '300'
                self.maconfig['Roadbooks'] = {}
                self.maconfig['Roadbooks']['etape'] = ''
                self.maconfig['Roadbooks']['case'] = '-1'
                self.maconfig.write(configfile)

	      # On le charge
        self.maconfig.read('RpiRoadbook.cfg')

        self.countdown = 4 ;
        self.iscountdown = True ;
        self.selection= 0 ;
        self.fenetre = 0 ;
        self.saved= self.maconfig['Roadbooks']['etape'] ;
        self.font = pygame.font.SysFont("cantarell", 24)
        self.filenames = [f for f in os.listdir('/mnt/piusb/') if re.search('.pdf$', f)]
        if len(self.filenames) == 0 : self.SwitchToScene(NoneScene())
        self.filename = self.saved if self.saved in self.filenames  else ''
        self.j = time.time()


    def ProcessInput(self, events, pressed_keys):
        for event in events:
            if event.type == pygame.KEYDOWN :
                self.iscountdown = False ;
                if event.key == pygame.K_RETURN:
                # Move to the next screen when the user pressed Enter
                    if self.filename != self.filenames[self.selection] :
                        self.filename = self.filenames[self.selection]
                        self.maconfig['Roadbooks']['etape'] = self.filenames[self.selection]
                        self.maconfig['Roadbooks']['case'] = '-1'
                        with open('RpiRoadbook.cfg', 'w') as configfile:
                            self.maconfig.write(configfile)
                    self.SwitchToScene(ConversionScene(self.filename))
                elif event.key == pygame.K_UP:
                    self.selection -= 1 ;
                    if self.selection < 0: self.selection = 0 ;
                    if self.selection < self.fenetre: self.fenetre -= 1
                    if self.fenetre < 0 : self.fenetre = 0
                elif event.key == pygame.K_DOWN:
                    self.selection += 1 ;
                    if self.selection == len(self.filenames): self.selection = len(self.filenames)-1 ;
                    if self.selection >= self.fenetre+10: self.fenetre+=1
            elif event.type == BOUTON21 :
                    self.iscountdown = False ;
                    self.selection -= 1 ;
                    if self.selection < 0: self.selection = 0 ;
                    if self.selection < self.fenetre: self.fenetre -= 1
                    if self.fenetre < 0 : self.fenetre = 0
            elif event.type == BOUTON26 :
                    self.iscountdown = False ;
                    self.selection += 1 ;
                    if self.selection == len(self.filenames): self.selection = len(self.filenames)-1 ;
                    if self.selection >= self.fenetre+10: self.fenetre+=1
            elif event.type == BOUTON20 :
                    self.iscountdown = False ;
                    if self.filename != self.filenames[self.selection] :
                        self.filename = self.filenames[self.selection]
                        self.maconfig['Roadbooks']['etape'] = self.filenames[self.selection]
                        self.maconfig['Roadbooks']['case'] = '-1'
                        with open('RpiRoadbook.cfg', 'w') as configfile:
                            self.maconfig.write(configfile)
                    self.SwitchToScene(ConversionScene(self.filename))

    def Update(self):
        if self.iscountdown:
            self.k = time.time();
            if (self.k-self.j>=self.countdown) :
                self.SwitchToScene(RoadbookScene(self.filename))

    def Render(self, screen):
        screen.fill((0, 0, 0))
        invite = self.font.render ('Sélectionnez le roadbook à charger :',0,(255,255,255))
        screen.blit(invite,(10,10))
        if self.fenetre > 0 :
            fleche_up = self.font.render('(moins)',0,(100,100,100))
            screen.blit (fleche_up,(10,50))
        for i in range (len(self.filenames)) :
            if i >= self.fenetre and i <self.fenetre+10 :
                couleur = (255,0,0) if self.filenames[i] == self.saved else (255,255,255)
                fond = (0,0,255) if i == self.selection else (0,0,0)
                text = self.font.render (self.filenames[i]+' (En cours)', 0, couleur,fond) if self.filenames[i] == self.saved else self.font.render (self.filenames[i], 0, couleur,fond)
                screen.blit (text,(10,80+(i-self.fenetre)*30))
        if self.fenetre+10<len(self.filenames):
            fleche_up = self.font.render('(plus)',0,(100,100,100))
            screen.blit (fleche_up,(10,380))
            # TODO : Limiter le nombre de lignes affichées et faire un scroll si trop de lignes.
        if self.iscountdown :
            text = self.font.render('Démarrage automatique dans '+str(int(self.countdown+1-(self.k-self.j)))+'s...', True, (0, 255, 0))
            screen.blit(text,(10,450))

#*******************************************************************************************************#
#---------------------------------------- La partie Pas de Roadbooks présents --------------------------#
#*******************************************************************************************************#
class NoneScene(SceneBase):
    def __init__(self, fname = ''):
        self.next = self
        self.filename = fname
        pygame.font.init()
        self.font = pygame.font.SysFont("cantarell", 24)
        self.img = pygame.image.load('./../Roadbooks/images/nothing.jpg')
        self.text1 = self.font.render('Aucun roadbook présent.', True, (0, 255, 0))
        self.text2 = self.font.render('Appuyez sur OK pour revenir', True, (0, 255, 0))
        self.text3 = self.font.render('au menu après téléversement', True, (0, 255, 0))

    def ProcessInput(self, events, pressed_keys):
        for event in events:
            if event.type == pygame.QUIT:
                self.Terminate()
            if event.type == BOUTON20:
                self.SwitchToScene(TitleScene())

    def Update(self):
        pass

    def Render(self, screen):
        screen.fill((0,0,0))
        screen.blit(self.text1, (100, 200))
        screen.blit(self.text2, (100, 230))
        screen.blit(self.text3, (100, 260))
        pygame.display.flip()

#*******************************************************************************************************#
#---------------------------------------- La partie Réglage de l'horloge -------------------------------#
#*******************************************************************************************************#
class SetClockScene(SceneBase):
    def __init__(self, fname = ''):
        self.next = self
        self.filename = fname
        pygame.font.init()
        self.font = pygame.font.SysFont("cantarell", 24)

    def ProcessInput(self, events, pressed_keys):
        pass

    def Update(self):
        pass

    def Render(self, screen):
        print("uh-oh, you didn't override this in the child class")


#*******************************************************************************************************#
#---------------------------------------- La partie Gadget Mass Storage --------------------------------#
#*******************************************************************************************************#
class G_MassStorageScene(SceneBase):
    def __init__(self, fname = ''):
        self.next = self
        self.filename = fname
        pygame.font.init()
        self.font = pygame.font.SysFont("cantarell", 24)

    def ProcessInput(self, events, pressed_keys):
        pass

    def Update(self):
        pass

    def Render(self, screen):
        print("uh-oh, you didn't override this in the child class")



#*******************************************************************************************************#
#------------------------- La partie Conversion en Image d'un fichier ----------------------------------#
#*******************************************************************************************************#
class ConversionScene(SceneBase):
    def __init__(self, fname = ''):
        self.next = self
        self.filename = fname
        pygame.font.init()
        self.font = pygame.font.SysFont("cantarell", 24)

    def ProcessInput(self, events, pressed_keys):
        pass

    def Update(self):
        pass

    def Render(self, screen):
        text1 = self.font.render('Préparation du roadbook... Patience...', True, (0, 255, 0))
        self.maconfig = configparser.ConfigParser()
        filedir = os.path.splitext(self.filename)[0]
        if os.path.isdir('./../Roadbooks/'+filedir) == False: # Pas de répertoire d'images, on convertit le fichier
            os.mkdir('./../Roadbooks/'+filedir)
						# on vérifie le format de la page :
            width, height = page_size ('/mnt/piusb/'+self.filename)
            if width > height :
                text2 = self.font.render('Conversion des cases en cours...', True, (0, 255, 0))
                total = page_count ('/mnt/piusb/'+self.filename)
                for i in range (total) :
                    screen.fill((0, 0, 0))
                    screen.blit(text1,(100,200))
                    screen.blit(text2,(100,230))
                    text = self.font.render('Case {}/{}'.format(i,total), True, (0, 255, 0))
                    screen.blit(text,(100,260))
                    self.pages = convert_from_path('/mnt/piusb/'+self.filename, output_folder='./../Roadbooks/'+filedir,first_page = i+1, last_page=i+1, dpi=150 , fmt='jpg')
                    pygame.display.flip()
            else:
                # conversion et découpage des cases
                screen.fill((0, 0, 0))
                screen.blit(text1,(100,200))
                text2 = self.font.render('Format Tripy détecté. Conversion en cours...', True, (0, 255, 0))
                screen.blit(text2,(100,230))
                nb_pages = page_count ('/mnt/piusb/'+self.filename)
                #Marge supperieur (pix)
                marge_up = 178
                #Hauteur d'une case (pix)
                hauteur = 177
                #Largeur d'une case (mm)
                largeur = 610
                #Milieu de page (mm)
                milieu = 615
                #Nombre de ligne par page
                nb_ligne = 8
                #Nombre de case par page
                nb_cases = nb_ligne * 2
                total = nb_pages * nb_cases

                w = round(largeur)
                h = round(hauteur)

                for i in reversed(range (nb_pages)) :
                    for j in reversed(range (nb_cases)):
                        if j < nb_ligne :
                            x = round(0)
                            y = round(marge_up+(nb_ligne-j-1)*hauteur)
                        else :
                            x = round(milieu)
                            y = round(marge_up+(2*nb_ligne-j-1)*hauteur)
                        text = self.font.render('Case {}/{}'.format(i*nb_cases+j+1,total), True, (0, 255, 0))
                        screen.fill((0, 0, 0))
                        screen.blit(text1,(100,200))
                        screen.blit(text2,(100,230))
                        screen.blit(text,(100,260))
                        self.pages = convert_from_path('/mnt/piusb/'+self.filename, output_folder='./../Roadbooks/'+filedir,first_page = i+1, last_page=i+1, dpi=150 , x=x,y=y,w=w,h=h,singlefile=str(total-i*nb_cases-j),fmt='jpg')
                        pygame.display.flip()
            # On charge le fichier de configuration
            self.maconfig.read('RpiRoadbook.cfg')
            # On se positionne à l'avant dernière case (ou la 2ème dans l'ordre de lecteur du rb
            self.maconfig['Roadbooks']['case'] = str(total-2)
            with open('RpiRoadbook.cfg', 'w') as configfile:
              self.maconfig.write(configfile)
        else:
            print('On fait une verification de coherence')
            filedir = os.path.splitext(self.filename)[0]
            nb_pages = page_count ('/mnt/piusb/'+self.filename)
            width, height = page_size ('/mnt/piusb/'+self.filename)
            nb_images = len([f for f in os.listdir('./../Roadbooks/'+filedir) if re.search('.jpg$', f)])
            if width > height :
                total = nb_pages
                if total != nb_images :
                    text2 = self.font.render('Pas le même nombre de cases ! On vérifie...', True, (0, 255, 0))
                    for i in range (total) :
                        screen.fill((0, 0, 0))
                        screen.blit(text1,(100,200))
                        screen.blit(text2,(100,230))
                        text = self.font.render('Case {}/{}'.format(i,total), True, (0, 255, 0))
                        screen.blit(text,(100,260))
                        self.pages = convert_from_path('/mnt/piusb/'+self.filename, output_folder='./../Roadbooks/'+filedir,first_page = i+1, last_page=i+1, dpi=150 , fmt='jpg')
                        pygame.display.flip()
            else :
                # Format Tripy
                print('Verification coherence Format Tripy')
                nb_ligne = 8
                #Nombre de case par page
                nb_cases = nb_ligne * 2
                total = nb_pages * nb_cases
                nb_images = len([f for f in os.listdir('./../Roadbooks/'+filedir) if re.search('.jpg$', f)])
                if total != nb_images :
                    text2 = self.font.render('Pas le même nombre de cases ! On vérifie...', True, (0, 255, 0))
                    #Marge supperieur (pix)
                    marge_up = 178
                    #Hauteur d'une case (pix)
                    hauteur = 177
                    #Largeur d'une case (mm)
                    largeur = 610
                    #Milieu de page (mm)
                    milieu = 615
                    #Nombre de ligne par page
                    nb_ligne = 8
                    #Nombre de case par page
                    nb_cases = nb_ligne * 2
                    total = nb_pages * nb_cases

                    w = round(largeur)
                    h = round(hauteur)

                    for i in reversed(range (nb_pages)) :
                        for j in reversed(range (nb_cases)):
                            if j < nb_ligne :
                                x = round(0)
                                y = round(marge_up+(nb_ligne-j-1)*hauteur)
                            else :
                                x = round(milieu)
                                y = round(marge_up+(2*nb_ligne-j-1)*hauteur)
                            screen.fill((0, 0, 0))
                            screen.blit(text1,(100,200))
                            screen.blit(text2,(100,230))
                            text = self.font.render('Case {}/{}'.format(i*nb_cases+j+1,total), True, (0, 255, 0))
                            screen.blit(text,(100,260))
                            self.pages = convert_from_path('/mnt/piusb/'+self.filename, output_folder='./../Roadbooks/'+filedir,first_page = i+1, last_page=i+1, dpi=150 , x=x,y=y,w=w,h=h,singlefile=str(total-i*nb_cases-j),fmt='jpg')
                            pygame.display.flip()
            # On charge le fichier de configuration
            self.maconfig.read('RpiRoadbook.cfg')
            if int(self.maconfig['Roadbooks']['case']) < 0 or int(self.maconfig['Roadbooks']['case']) > total -2 :
              # Pb avec la position sauvegardée. On se positionne à l'avant dernière case (ou la 2ème dans l'ordre de lecteur du rb
              self.maconfig['Roadbooks']['case'] = str(total-2)
              with open('RpiRoadbook.cfg', 'w') as configfile:
                self.maconfig.write(configfile)

        self.SwitchToScene(RoadbookScene(self.filename))


#*******************************************************************************************************#
#------------------------- La partie Dérouleur ---------------------------------------------------------#
#*******************************************************************************************************#
class RoadbookScene(SceneBase):
    def __init__(self, fname = ''):
        SceneBase.__init__(self,fname)

        self.maconfig = configparser.ConfigParser()

	    # Vérification de l'existence du fichier de config
        try:
            with open('RpiRoadbook.cfg'): pass
        except IOError:
            with open('RpiRoadbook.cfg', 'w') as configfile:
                self.maconfig['Parametres_Odometre']={}
                self.maconfig['Parametres_Odometre']['roue'] = '1860'
                self.maconfig['Parametres_Odometre']['nb_aimants'] = '1'
                self.maconfig['Parametres_Odometre']['totalisateur'] = '0'
                self.maconfig['Roadbooks'] = {}
                self.maconfig['Roadbooks']['etape'] = ''
                self.maconfig['Roadbooks']['case'] = '-1'
                self.maconfig.write(configfile)
        # On le charge
        self.maconfig.read('RpiRoadbook.cfg')
        self.filedir = os.path.splitext(self.filename)[0]

        #Chargement des images
        fichiers = [name for name in os.listdir('./../Roadbooks/'+self.filedir) if os.path.isfile(os.path.join('./../Roadbooks/'+self.filedir, name))]
        self.nb_cases = len(fichiers)
        self.case = int(self.maconfig['Roadbooks']['case'])
        if self.case < 0 :
            self.case = self.nb_cases - 2 # on compte de 0 à longueur-1, on se place sur l'avant dernière case si 1ère ouverture
        self.oldcase = self.case
        self.pages = []
        for i in fichiers:
            self.pages.append (pygame.image.load(os.path.join('./../Roadbooks/'+self.filedir,i)))  # On a converti toutes les images. c'est plus long au début mais plus réactif ensuite...

        pygame.font.init()
        self.font = pygame.font.SysFont("cantarell", 72)
        self.myfont_36 = pygame.font.SysFont("cantarell", 36)
        self.myfont_70 = pygame.font.SysFont("cantarell", 70)
        self.myfont_100 = pygame.font.SysFont("cantarell", 100)

        self.label_tps = self.myfont_70.render("00:00:00", 1, (200,200,200))
        self.label_km = self.myfont_100.render("000.00", 1, (200,200,200))
        self.label_vi = self.myfont_70.render("000", 1, (200,200,200))
        self.label_vm = self.myfont_70.render("000", 1, (100,100,100))

    def ProcessInput(self, events, pressed_keys):
        global distance,tpsinit,cmavant,j,vmoy,vmax
        for event in events:
            if event.type == pygame.QUIT:
                self.Terminate()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.Terminate()
                if event.key == pygame.K_UP:
                    self.oldcase = self.case
                    self.case += 1
                if event.key == pygame.K_DOWN:
                    self.oldcase = self.case
                    self.case -= 1
                if event.key == pygame.K_HOME:
                    self.oldcase = self.case
                    self.case = self.nb_cases -1
                if event.key == pygame.K_END:
                    self.oldcase = self.case
                    self.case = 1
            elif event.type == BOUTON16:
                distance+=1000
                cmavant=distance
                j = time.time()
            elif event.type == BOUTON26:
                self.oldcase = self.case
                self.case -= 1
            elif event.type == BOUTON21:
                self.oldcase = self.case
                self.case += 1
            elif event.type == BOUTON19:
                distance-=1000
                if distance <= 0 : distance = 0
                cmavant = distance
                j = time.time();
            elif event.type == BOUTON20:
                distance = 0.0
                cmavant = distance 
                vmoy = 0
                speed = 0
                tpsinit = time.time()/1000
                vmax = 0;

        # Action sur le dérouleur
        if self.case > self.nb_cases - 2 :
            self.case = self.nb_cases -2
        if self.case < 0 :
            self.case = 0

    def Update(self):
        global distance,speed,vmax,cmavant,tps,j,vmoy
        if self.case != self.oldcase :
            # On sauvegarde la nouvelle position
            self.maconfig['Roadbooks']['case'] = str(self.case)
            try:
              with open('RpiRoadbook.cfg', 'w') as configfile:
                self.maconfig.write(configfile)
            except: pass

        if distance < 2000 or tps < 2 : 
            vmoy = 0 # On maintient la vitesse moyenne à 0 sur les 20 premiers mètres ou les 2 premières secondes
        else:
            vmoy = ((distance/(time.time()-tpsinit))*3600/100000);

        if ((time.time()-2) >= j) : 
            speed = (distance*36-cmavant*36); 
            speed = speed/2000; 
            j = time.time()
            cmavant = distance

        if speed > vmax : vmax = speed

        self.label_tps = self.myfont_70.render(time.strftime("%H:%M:%S", time.localtime()), 1, (200,200,200))
        self.label_km = self.myfont_100.render('{0:.2f}'.format(distance/100000), 1, (200,200,200))
        self.label_t_vi = self.myfont_36.render('Vitesse',1,(200,0,0))
        self.label_vi = self.myfont_70.render('{0:.0f}'.format(speed), 1, (200,200,200))
        self.label_t_vm = self.myfont_36.render('VMax',1,(200,0,0))
        self.label_vm = self.myfont_70.render('{0:.0f}'.format(vmax), 1, (100,100,100))

    def Render(self, screen):
        screen.fill((0,0,0))
	    # Positionnement des différents éléments d'affichage
        screen.blit(self.label_tps, (10, 5))
        screen.blit(self.label_km, (600, -10))
        screen.blit(self.label_t_vi,(630,120))
        screen.blit(self.label_vi, (700, 200))
        screen.blit(self.label_t_vm, (630,320))
        screen.blit(self.label_vm, (700, 400))
        screen.blit (self.pages[self.case],(0,100))
        screen.blit (self.pages[self.case+1],(0,300))



# Pour optimisation
#import cProfile
#cProfile.run ('run_RpiRoadbook(800, 480, 60, TitleScene())')

run_RpiRoadbook(800, 480, 60, TitleScene())
