#!/usr/bin/python
#
# Copyright Hugh Perkins 2015 hughperkins at gmail
#
# This Source Code Form is subject to the terms of the Mozilla Public License, 
# v. 2.0. If a copy of the MPL was not distributed with this file, You can 
# obtain one at http://mozilla.org/MPL/2.0/.

# assumptions:
# - at least python 2.7
# - not python 3.x
# - internet is available

import sys,os,time, os.path
import urllib
import zipfile
import shutil
import numpy
import GoBoard

from os import sys, path
mydir = path.dirname(path.abspath(__file__))
print mydir
sys.path.append(mydir + '/gomill' )
import gomill
import gomill.sgf

sKgsUrl = 'http://u-go.net/gamerecords/'

def downloadPage( url ):
    fp = urllib.urlopen(url)
    data = fp.read()
    fp.close()
    return data

def downloadFiles( sTargetDirectory, iMaxFiles ):
    global sKgsUrl
    # first, ocunt how many we've downlaoded ,to save downlaoding the index page again
    if iMaxFiles != -1:
        iCount = 0
        for sFilename in os.listdir( sTargetDirectory ):
            sFilepath = sTargetDirectory + '/' + sFilename
            if os.path.isfile( sFilepath ) and not sFilename.startswith('~'):
                iCount = iCount + 1
        if iCount >= iMaxFiles:
            print 'reached limit of files you requested, skipping other downlaods'
            return
    
    page = downloadPage( sKgsUrl )
#    print page
    splitpage = page.split('<a href="')
    iCount = 0
    for downloadUrlBit in splitpage:
        if downloadUrlBit.startswith( "http://" ):
            downloadUrl = downloadUrlBit.split('">Download')[0]
            if downloadUrl.endswith('.zip'):
                print downloadUrl
                sFilename = os.path.basename( downloadUrl )
                if not os.path.isfile( sTargetDirectory + '/' + downloadUrl ):
                    print 'downloading ' + downloadUrl + ' ... '
                    urllib.urlretrieve ( downloadUrl, sTargetDirectory + '/~' + sFilename )
                    os.rename( sTargetDirectory + '/~' + sFilename, sTargetDirectory + '/' + sFilename )
        iCount = iCount + 1
        if iMaxFiles != -1 and iCount > iMaxFiles:
            print 'reached limit of files you requested, skipping other downlaods'
            return

def unzipFiles( sTargetDirectory, iMaxFiles ):
    iCount = 0
    for sFilename in os.listdir( sTargetDirectory ):
        sFilepath = sTargetDirectory + '/' + sFilename
        if os.path.isfile( sFilepath ) and not sFilename.startswith('~'):
            #print sFilepath
            thiszip = zipfile.ZipFile( sFilepath )
            zipdirname = thiszip.namelist()[0]
            if not os.path.isdir( sTargetDirectory + '/' + zipdirname ):
                print 'unzipping ' + sFilepath + '...'
                thiszip.extractall( sTargetDirectory + '/~' + zipdirname )
                shutil.move( sTargetDirectory + '/~' + zipdirname + '/' + zipdirname, sTargetDirectory )
                os.rmdir( sTargetDirectory + '/~' + zipdirname )
            iCount = iCount + 1
            if iMaxFiles != -1 and iCount > iMaxFiles:
                print 'reached limit of files you requested, skipping other unzips'
                return

def addToDataFile( datafile, color, move, goBoard ):
    # color is the color of the next person to move
    # move is the move they decided to make
    # goBoard represents the state of the board before they moved
    # - we should flip the board and color so we are basically always black
    # - we should calculate liberties at each position
    # - we should get ko
    # - and we should write to the file :-)
    #
    # planes we should write:
    # 0: our stones with 1 liberty
    # 1: our stones with 2 liberty
    # 2: our stones with 3 or more liberties
    # 3: their stones with 1 liberty
    # 4: their stones with 2 liberty
    # 5: their stones with 3 or more liberty
    # 6: simple ko
    # 7: board... 
    (row,col) = move
    enemyColor = goBoard.otherColor( color )
    datafile.write('GO') # write something first, so we can sync/validate on reading
    datafile.write(chr(row)) # write the move
    datafile.write(chr(col))
    for row in range( 0, goBoard.boardSize ):
        for col in range( 0, goBoard.boardSize ):
            thisbyte = 0
            pos = (row,col)
            if goBoard.board.get(pos) == color:
                if goBoard.goStrings[pos].liberties.size() == 1:
                    thisbyte = thisbyte | 1
                elif goBoard.goStrings[pos].liberties.size() == 2:
                    thisbyte = thisbyte | 2
                else:
                    thisbyte = thisbyte | 4
            if goBoard.board.get(row,col) == enemyColor:
                if goBoard.goStrings[pos].liberties.size() == 1:
                    thisbyte = thisbyte | 8
                elif goBoard.goStrings[pos].liberties.size() == 2:
                    thisbyte = thisbyte | 16
                else:
                    thisbyte = thisbyte | 32
            if goBoard.isSimpleKo( color, pos ):
                thisbyte = thisbyte | 64
            thisbyte = thisbyte | 128
            datafile.write( chr(thisbyte) )

def walkthroughSgf( datafile, sgfContents ):
    sgf = gomill.sgf.Sgf_game.from_string( sgfContents )
    # print sgf
    if sgf.get_size() != 19:
        print 'boardsize not 19, ignoring'
        return
    if sgf.get_handicap() != None and sgf.get_handicap() != 0:
        print 'handicap not zero, ignoring (' + str( sgf.get_handicap() ) + ')'
        return
    goBoard = GoBoard.GoBoard(19)
    doneFirstMove = False
    moveIdx = 0
    for it in sgf.main_sequence_iter():
        (color,move) = it.get_move()
        #print 'color ' + str(color)
        #print move
        if color != None and move != None:
            (row,col) = move
            if doneFirstMove and datafile != None:
                addToDataFile( datafile, color, move, goBoard )
            #print 'applying move ' + str( moveIdx )
            goBoard.applyMove( color, (row,col) )
            moveIdx = moveIdx + 1
            doneFirstMove = True
            #if moveIdx >= 120:
            #    sys.exit(-1)
    print goBoard
    #print 'winner: ' + sgf.get_winner()

def loadSgf( datafile, sgfFilepath ):
    sgfile = open( sgfFilepath, 'r' )
    contents = sgfile.read()
    sgfile.close()
#        print contents
    if contents.find( 'SZ[19]' ) < 0:
        print 'not 19x19, skipping'
        return
    try:
        walkthroughSgf( datafile, contents )
    except:
        print "exception caught for file " + path.abspath( sgfFilepath )
        raise 
    print sgfFilepath

def loadAllSgfs( datafile, sDirPath ):
    iCount = 0
    for sSgfFilename in os.listdir( sDirPath ):
        print sSgfFilename
        loadSgf( datafile, sDirPath + '/' + sSgfFilename )
        iCount = iCount + 1
#        if iCount > 1:
#            return

def loadAllUnzippedDirectories( sTargetDirectory, iMaxFiles ):
    iCount = 0
    for sDirname in os.listdir( sTargetDirectory ):
        sDirpath = sTargetDirectory + '/' + sDirname
        if os.path.isdir( sDirpath ) and not sDirname.startswith('~'):
            # create a data file for this directory, and read the sgfs into it...
            datafile = open( sTargetDirectory + '/' + sDirname + '.dat', 'wb' )
            loadAllSgfs( datafile, sDirpath )
            datafile.write('END')
            datafile.close()
            iCount = iCount + 1
            if iCount > iMaxFiles:
                return

def go(sTargetDirectory, iMaxFiles):
    print 'go'
    if not os.path.isdir( sTargetDirectory ):
        os.makedirs( sTargetDirectory )
    downloadFiles( sTargetDirectory, iMaxFiles )
    unzipFiles( sTargetDirectory, iMaxFiles )
    loadAllUnzippedDirectories( sTargetDirectory, iMaxFiles )

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: ' + sys.argv[0] + ' [targetdirectory] [[maxfiles]]'
        print '[maxfiles] is optional argument, to limit how many files to download/process'
        sys.exit(-1)
    sTargetDirectory = sys.argv[1]
    iMaxFiles = -1
    if len(sys.argv) >= 3:
        iMaxFiles = int( sys.argv[2] )
    go(sTargetDirectory, iMaxFiles)

