

"""
Contains functions for running the new methods of analyzing the foils.
"""
import cv2
import numpy as np
from scipy import misc

import GenSIP.functions as fun
import GenSIP.kuwahara as Kuwahara
import GenSIP.bigscans.images as images
import GenSIP.sandbox.Histograms as hist
import GenSIP.sandbox.datatools as dat
import GenSIP.sandbox.binaryops as binops
import GenSIP.measure as meas
import GenSIP.sandbox.foldertools as fold
import GenSIP.sandbox.display as dis

import os
import csv
from socket import gethostname

###################################################################################

###################################################################################

def resultsToCSV(resultsDict, path, name, **kwargs):
    """
    Takes the resultsDict from any of the newmethod functions, and creates a 
    CSV file at the path that has a row for each subImage in a results dictionary,
    and a column for each piece of the results data for the subImg. 
    This function should be easily generalized to receive any dictionary with the
    format:
        resultsDict = {
                    'item1':{'result1':<str or number>,
                            ...
                            'resultN':<str or number>
                            },
                            
                            ...
                            
                    'itemN':{'result1':<str or number>,
                            ...
                            'resultN':<str or number>
                            }  
                        }   
                        
        In general 'item1' to 'itemN' will be the subimage names. 
         
        Inputs:
            - resultsDict - results dictionary formatted as described above.
            - path - the path to the folder that will contain the csv file
            - name - Name of the test or set of images, or larger image that 
                contains all of the subImages. 
        Key-Word Arguments:
            - FirstColHead = 'SubImage' - Header for the rows of items. Default
                set to 'SubImage'
            - FileHeader = 'Standard' - Header of the csv file. If given, should
                be a list in which each item is a list that designates what goes
                into that row.
                If it is set to a string 'None', no header will be given.
                If it is set to a string 'Standard' it will give the standard 
                header of the format:
                    "GenSIP newmethod Data", '', <name>
                    "Date:", <datestring>
                    "Computer:", <host>, "Version", <Version>],
    """            
    ItemHeader = kwargs.get('FirstColHead','SubImage')
    
    Columns = [ItemHeader]
    names = resultsDict.keys()
    names.sort()
    Rows = []
    for sub in names:
        if type(resultsDict[sub])==dict:
            Keys = resultsDict[sub].keys()
            Keys.sort()
            # Make sure all the keys in the subImg dictionary are 
            # accounted for in the Columns
            Columns.extend([k for k in Keys if (type(resultsDict[sub][k])!=dict) and not(k in Columns)])
            # Create the row in the csv file
            row = [sub]
            for col in Columns[1:]:
                entry = resultsDict[sub].get(col,"'--")
                row.append(entry)
            Rows.append(row)
    # Create csv file:
    
    datestring = fun.getDateString()
    host = os.path.splitext(gethostname())[0]
    Version = fun.getGenSIPVersion()

    TitleRows = [
                 ["GenSIP newmethod Data",'',name],
                 ["Date:",datestring],
                 ["Computer:",host,"Version",Version],
                  Columns]
    if path.endswith('.csv'):
        resultsCSV = open(path, 'w+b')
    else:
        if not(path.endswith('/')): path = path+'/'
        resultsCSV = open(path+"Results.csv", 'w+b')
    resWriter = csv.writer(resultsCSV)
    resWriter.writerows(TitleRows)
    resWriter.writerows(Rows)
            
###################################################################################

###################################################################################

def runOnSubImgs(folderpath, maskPath, res, name, writeToCSV=True,
                 genPoster = False, exten='.tif', verbose=True, genResults=True):
    """
    Runs newmethod analyzeImg on a folder of sub images.
    
    """
    subImgs = os.listdir(folderpath)
    subImgs = fold.FILonlySubimages(subImgs)
    masks = os.listdir(maskPath)
    masks = fold.FILonlySubimages(masks)
    subImgs.sort()
    masks.sort()
    if not(folderpath.endswith('/')):
        folderpath = folderpath+'/'
    if not(maskPath.endswith('/')):
        maskPath = maskPath+'/'
    subNames = [i.strip(exten) for i in subImgs]
    for sub in subImgs:
        # Make the paths complete
        subImgs[subImgs.index(sub)] = folderpath+sub
        
        try: masks[masks.index(sub)] = maskPath+sub
        except: 
            print sub, maskPath
            return
            
    outFolders = ["Output/"+name,
                  "Output/"+name+"/DirtMaps",
                  "Output/"+name+"/PtMaps",
                  "Output/"+name+"/PosterMaps"]
                  
    if genPoster==False:
        outFolders=outFolders[:-1]
    for f in outFolders:
        if not(os.path.exists(f)):
            os.mkdir(f)
    # initiate results dictionary.
    Results = {}
    for i in range(len(subNames)):
        if verbose: print subNames[i]
        img = fun.loadImg(subImgs[i])
        mask = fun.loadImg(masks[i])
        if genPoster:
            PtMap, DirtMap, Data, post = analyzeImg(img,res,returnPoster=True,Mask=mask,verbose=verbose)
            cv2.imwrite("Output/"+name+"/PosterMaps/"+subNames[i]+".png",
                        post, [cv2.cv.CV_IMWRITE_PNG_COMPRESSION,6])
        else:
            PtMap, DirtMap, Data = analyzeImg(img,res,returnPoster=False,Mask=mask,verbose=verbose)
        # Remove the results from the Data dictionary and put them in the results
        # Dictionary. If the Data dictionary somehow does not have one of the results,
        # that entry in the Results dictionary is set to "ERROR".
        Results[subNames[i]]={}
        Results[subNames[i]]['PtArea'] = Data.pop('PtArea',"ERROR")
        Results[subNames[i]]['dirtArea'] = Data.pop('dirtArea',"ERROR")
        Results[subNames[i]]['dirtNum'] = Data.pop('dirtNum',"ERROR")
        '''
        for reg in Data[subNames[i]]:
            Results[subNames[i]][reg] = {}
            Results[subNames[i]][reg]['PlatThresh'] = Data.get('PtThresh',"ERROR")
            Results[subNames[i]][reg]['DirtThresh'] = Data.get('DirtThresh',"ERROR")
            Results[subNames[i]][reg]['MoPeak'] = Data.get('MoPeak',"ERROR")
        '''
        dis.saveHist(Data, "Output/"+name, name=subNames[i])
        
        cv2.imwrite("Output/"+name+"/DirtMaps/"+subNames[i]+".png",
                    DirtMap.astype(np.uint8)*255, 
                    [cv2.cv.CV_IMWRITE_PNG_COMPRESSION,6])
        cv2.imwrite("Output/"+name+"/PtMaps/"+subNames[i]+".png",
                    PtMap.astype(np.uint8)*255, 
                    [cv2.cv.CV_IMWRITE_PNG_COMPRESSION,6])
                    
    images.stitchImage("Output/"+name+"/DirtMaps")
    images.stitchImage("Output/"+name+"/PtMaps")
    
    if genPoster:
        images.stitchImage("Output/"+name+"/PosterMaps")
    if genResults: return Results
    
###################################################################################

###################################################################################

def testonStandard (name, res, returnPoster=False, returnMask=False,verbose=True,returnStandards=False):
    """
    Runs newmethod analysis on a standard. Returns the results of newmethod analysis as 
    well as a dictionary giving the error of the different measurements relative to 
    the standard.
    """
    img = fun.loadImg("standards/"+name+"/"+name+".tif")
    try: mask = fun.loadImg("standards/"+name+"/mask.tif")
    except: mask = 0
    
    PtMap,DirtMap,Data,post = analyzeImg(img,res,returnPoster=returnPoster,Mask=0,verbose=verbose)
    STDPtMap = fun.loadImg("standards/"+name+"/"+"plat.png")
    STDDirtMap = fun.loadImg("standards/"+name+"/"+"dirt.png")
    STDdirtArea, STDdirtNum = meas.calcDirt(STDDirtMap, res)
    STDPtArea = meas.calcExposedPt(STDPtMap,res)
    
    ErrorDirtArea = round(float((STDdirtArea-Data["dirtArea"]))/STDdirtArea,3)
    ErrorDirtNum = round(float((STDdirtNum-Data["dirtNum"]))/STDdirtNum,3)
    ErrorPtArea = round(float((STDPtArea-Data["PtArea"]))/STDPtArea,3)
    errorDict = {
    "ErrorDirtArea":ErrorDirtArea,
    "ErrorDirtNum":ErrorDirtNum,
    "ErrorPtArea":ErrorPtArea}
    if returnStandards:
        return errorDict,PtMap,DirtMap,Data,STDPtMap,STDDirtMap
    else:
        return errorDict,PtMap,DirtMap,Data
        
###################################################################################

###################################################################################
'''
def anImgCalWrapper(img,res,returnPoster=False,Mask=0,verbose=True, MoDirt = 'Mo'):
    """
    Runs analazeImg and reformats the output for measure.compareToStandards
    
    """
    PtMap, DirtMap, Data, post = analyzeImg(img,res,returnPoster=True,Mask=Mask,verbose=verbose)
    if fun.checkMoDirt(MoDirt) == 'mo':
        ret = [PtMap, Data,post]
    elif fun.checkMoDirt(MoDirt)== 'dirt':
        ret = [DirtMap, Data, post]
    if returnPoster:
        return tuple(ret)
    else:
        return tuple(ret[:-1])
'''

###################################################################################

###################################################################################

def analyzeByHisto(img,res,Mask=0,verbose=True,
                MoDirt='mo',returnPoster=False,returnData=False,returnSizes=True):
    """
    Runs the newmethod analysis on an image. 
    
    """
    if MoDirt!='both':
        MoDirt=fun.checkMoDirt(MoDirt)
        
    # Make the poster
    proc = PosterPreProc(img,Mask=Mask,ExcludePt=True)
    post = images.bigPosterfy(proc)
    # Analyze the image with MakeRegions and New RegThresh
    Data = MakeRegions(img,post,Mask=Mask)
    PtMap, DirtMap, Data = NewRegThresh(img,
                                        Data,
                                        Mask=Mask,
                                        returnData=True,
                                        verbose=verbose)
                                        
    # Make sure that the Dirt and Pt maps are binary images of 0 and 1
    DirtMap[DirtMap!=0]=1
    PtMap[PtMap!=0]=1
    
    # Extract the foil area from the Data dictionary
    FoilArea = getFoilArea(Data)*res*10**-6
    
    # Calculate the Pt Area
    PtArea = meas.calcExposedPt(PtMap,res, getAreaInSquaremm=True)
    
    # Calculate the Percent of area that is exposed Pt
    if FoilArea == 0:
        PercPt = 0
    else:
        PercPt = round((float(PtArea)/float(FoilArea))*100,2)
        
    # Calculate dirt area, number, sizes, and produce labelled image
    dirtArea, dirtNum,dirtSizes,labeled = meas.calcDirt(DirtMap,
                                                        res, 
                                                        returnSizes=True,
                                                        returnLabelled=True, 
                                                        getAreaInSquaremm=True) 
    if verbose:
        print "dirt Area: " + str(dirtArea)   
        print "dirt part number: " + str(dirtNum)
        print "Sizes: " + str(dirtSizes)
        
    # Make the return tuples depending on the value of MoDirt and the return 
    # options returnPoster, returnData, and returnSizes
    if MoDirt=='mo':
        stats = [PtArea, PercPt]
        picts = [PtMap]
        
    elif MoDirt=='dirt':
        stats = [dirtNum,dirtArea]
        if returnSizes:
            stats.append(dirtSizes)
        picts = [DirtMap]
        
    elif MoDirt=='both':
        stats = [PtArea, PercPt, dirtNum, dirtArea]
        if returnSizes:
            stats.append(dirtSizes)
        picts = [PtMap, DirtMap]
        
    stats.append(FoilArea)
    
    if returnData:
        stats.append(Data)
        
    if returnPoster:
        picts.append(post)
        
    return tuple(stats), tuple(picts)
    
###################################################################################

###################################################################################

def getFoilArea (Data):
    """ 
    Returns the total foil area (in Pixels) of all of the regions of the 
    data dictionary
    """
    areaSum = 0
    for reg in Data:
        areaSum += Data[reg]['RegMask'].sum()
    return areaSum
        
        
###################################################################################

###################################################################################

def analyzeMoly(img,res,MoDirt='Mo',returnPoster=False,returnMask=False,Mask=0):
    """
    Runs the newmethod analysis on an image. 
    
    """
    IMG = img.astype(np.uint8)
    #print str(IMG[0:20])
    assert (IMG.sum()!=0),"Image is black!"
    proc = PosterPreProc(IMG)

    poster = images.bigPosterfy(proc)
    if type(Mask)==np.ndarray:
        mask = Mask
    else:
        mask = bigMaskEdges(IMG,res,Bkgrdthreshold=90)
    #print str(mask[0:20])
    if mask.sum()!=0: print "Everything is masked."
    assert (len(mask[mask==1]>len(mask[mask==0]))),"Mask is mostly black!"
    thresh,Data=NewRegThresh(IMG, poster, Mask=mask,gaussBlur=3,MoDirt=MoDirt,returnData=True)
    
    # Generate list of items to return and check if the poster or mask should be
    # returned.
    ret = [thresh,Data]
    if returnPoster:
        ret.append(poster)
    if returnMask:
        ret.append(mask)
    # Return everything as a tuple rather than a list
    return tuple(ret)

###################################################################################

###################################################################################

def PosterPreProc(image,**kwargs):
    """
    This method takes the image of the foil and creates a smoothed Kuwahara image
    used to make the poster for regional thresholding.
    
        Key-word Arguments:
            Mask = 0 - Assign the Mask here
            kern = 6 - Kernal size for poster opening and closing steps
            KuSize = 17 - Size of Kuwahara Filter
            Gaus1 = 5 - Size of first Gaussian Blur
            Gaus2 = 3 - Size of second Gaussian Blur
            rsize = .1 - Resize value
            Kuw_only = False - Option to only return the Kuwahara filtered image
            ExcludeDirt = True - Option to Exclude dirt 
    """
    Mask = kwargs.get("Mask",0) # Assign the Mask here
    kern = kwargs.get("kern",6) # Kernal size for poster opening and closing steps
    KuSize = kwargs.get("KuSize",17) # Size of Kuwahara Filter
    Gaus1 = kwargs.get("Gaus1",5) # Size of first Gaussian Blur
    Gaus2 = kwargs.get("Gaus2",3) # Size of second Gaussian Blur
    rsize = kwargs.get("rsize",.1) # Resize value
    Kuw_only = kwargs.get("Kuw_only",False) # Option to only return the Kuwahara filtered image
    ExcludeDirt = kwargs.get("ExcludeDirt",True) # Option to Exclude dirt from approximation of shading 
    ExcludePt = kwargs.get("ExcludePt",False) 
    img = np.copy(image).astype(np.uint8)
    
    # Calculate the average Apply mask if provided
    if type(Mask)==np.ndarray and Mask.shape==image.shape:
        if Mask.all() == 0:
            averageColor = 0
        else:
            averageColor = int(np.average(img[(Mask!=0)&(img>=10)&(img<=245)]))
    else:
        averageColor = int(np.average(img[(img>=10)&(img<=245)]))
        
    if ExcludeDirt:
        img[img<=40]=averageColor
    if ExcludePt:
        img[img>=(img.max()-10)]=averageColor
        
    if type(Mask)==np.ndarray and Mask.shape==image.shape:
        img[Mask==0]=averageColor
    
    proc = img.astype(np.uint8)
    proc = misc.imresize(proc,rsize)
    proc = cv2.morphologyEx(proc,cv2.MORPH_ERODE, (kern,kern)) # Eliminates most platinum spots
    proc = cv2.morphologyEx(proc,cv2.MORPH_DILATE,(kern+1,kern+1)) # Eliminates most dirt spots
    proc = cv2.GaussianBlur(proc,(Gaus1,Gaus1),0)
    proc = Kuwahara.Kuwahara(proc,KuSize)
    if Kuw_only:
        return proc
    proc = cv2.GaussianBlur(proc,(Gaus2,Gaus2),0)
    proc = misc.imresize(proc,img.shape)
    return proc

###################################################################################

###################################################################################

def NewRegThresh(ogimage, Data, Mask=0, MoDirt='Mo', returnData = False, verbose=False):
    """
    Creates thresholded images and modifies the Data dictionary for a given image.
    
    """

    # Clean up data dictionary. Maxreg is the region with the largest area
    Data = cleanUpRegData(Data) 
    Data,Maxreg = findMaxReg(Data)
       

    # Initiate the platinum, Area, Molybdenum, and Dirt Sums for each region.
    Ptsum = 0
    Allsum = 0
    MoSum = 0
    DirtSum = 0
    CrackSum = 0
    
    PtMap = np.zeros(ogimage.shape).astype(np.uint8)
    DirtMap = np.zeros(ogimage.shape).astype(np.uint8)
    
    for reg in Data:
        #  Set Threshold value for Pt
        numPx = sum(Data[reg]['Histogram'])
        # If the region is too small, then use the Pt threshold level of the largest
        # region
        if numPx<2000:
            PtThresh = hist.selectPtThresh(Data[Maxreg])
            DirtThresh = hist.selectDirtThresh(Data[Maxreg])
            Data[reg]['PtThresh'] = PtThresh
            Data[reg]['DirtThresh'] = DirtThresh
        else:
            PtThresh = hist.selectPtThresh(Data[reg])
            DirtThresh = hist.selectDirtThresh(Data[reg])
            Data[reg]['PtThresh'] = PtThresh
            Data[reg]['DirtThresh'] = DirtThresh
        # Make the PtMap using the applyPtThresh function.
        Data[reg]['PtMap'] = applyPtThresh(ogimage,PtThresh,\
        regionMask=Data[reg]['RegMask'],Mask=Mask).astype(np.bool_)
        # Make the DirtMap using the applyDirtThresh function.
        Data[reg]['DirtMap'] = applyDirtThresh(ogimage,DirtThresh,\
        regionMask=Data[reg]['RegMask'],Mask=Mask).astype(np.bool_)
        Data[reg]['MolyMap']=getMolyMap(Data[reg]['DirtMap'],Data[reg]['PtMap'],\
        regionMask=Data[reg]['RegMask'],Mask=Mask).astype(np.bool_)
        # Combine to 
        PtMap += Data[reg]['PtMap']
        DirtMap += Data[reg]['DirtMap']
        Ptsum += meas.calcExposedPt(Data[reg]['PtMap'],1)
        DirtSum += meas.calcDirt(Data[reg]['DirtMap'],1)[0] 
        MoSum += meas.calcExposedPt(Data[reg]["MolyMap"],1)
        
        
    Allsum = Ptsum+DirtSum+MoSum
    if verbose:
        try: PercPt = int(100*Ptsum/Allsum)
        except ZeroDivisionError: PercPt = np.nan
        print str(Ptsum)
        print "Percent Pt: " + str(PercPt)
        
        try: PercDirt = int(100*DirtSum/Allsum)
        except ZeroDivisionError: PercDirt = np.nan

        print str(DirtSum)
        print "Percent Dirt: " + str(PercDirt)  
        
    if returnData:
        return PtMap, DirtMap, Data
    else:
        return PtMap,DirtMap
        """
        if fun.checkMoDirt(MoDirt)=='mo':
            if returnData:
                return PtMap, Data
            else:
                return PtMap
        elif fun.checkMoDirt(MoDirt)=='dirt':
            if returnData:
                return DirtMap,Data
            else:
                return DirtMap
        """

###################################################################################

###################################################################################

def cleanUpRegData(Data):
    """
    Removes regions from the data dictionary that are not in the poster (and hence
    simply say 'Null').
    Runs "FilterFeatures" on the regions that are in the poster. 
    """

    for reg in Data.keys():
        if Data[reg] == 'Null':
            del Data[reg]
        else:
            Data[reg] = FilterFeatures(Data[reg])

    return Data
    
def findMaxReg(Data):
    "Finds the largest region in an image using its Data Dictionary."
    largest = 0
    Maxreg = ''
    for reg in Data.keys():
        numPx = sum(Data[reg]['Histogram'])
        if numPx > largest:
            largest = numPx
            Maxreg = reg     
    if Maxreg=='':
        print "No Max region found. Set to 'Mo'."
        print largest
        print 'Keys'+str(Data.keys())
        if 'Mo' in Data.keys(): Maxreg = 'Mo'
        else: 
            print "'Mo' not in Data dictionary. Set to first key in Data dictionary."
            Keys = Data.keys()
            Keys.sort()
            Maxreg = Keys[0]

    return Data,Maxreg

###################################################################################

###################################################################################

def MakeRegions(ogimage,poster,Mask=0,gaussBlur=3):
    """
     This Function breaks up an image into subregions and returns a dictionary 
     containing information on each subregion that can be used for further anal-
     ysis and for setting the threshold levels. 
     
    """
    if poster.shape != ogimage.shape:
        raise Exception("The two arrays are not the same shape.")
        return
    Image = ogimage.astype(np.uint8)
    gPoster = poster.astype(np.uint8)    

    if type(Mask)==int:
        Mask = np.ones(ogimage.shape)
    
    # Analyze histogram for each section:

    blkHisto, Bins = np.histogram(Image[(gPoster==0)&(Mask!=0)],256,(0,255))
    pleatHisto, Bins = np.histogram(Image[(gPoster==50)&(Mask!=0)],256,(0,255))
    dMoHisto, Bins = np.histogram(Image[(gPoster==85)&(Mask!=0)],256,(0,255))
    MoHisto, Bins = np.histogram(Image[(gPoster==150)&(Mask!=0)],256,(0,255))
    highExHisto, Bins = np.histogram(Image[(gPoster==200)&(Mask!=0)],256,(0,255))
    PlatHisto, Bins = np.histogram(Image[(gPoster==255)&(Mask!=0)],256,(0,255))
    
    # Put together the labels for the regions Dictionary
    regions = {}
    labels = ['blk','pleat','darkMo','Mo','highEx','Plat']

    graylevels = [0,50,85,150,200,255]
    histos = [blkHisto,pleatHisto,dMoHisto,MoHisto,highExHisto,PlatHisto]
    #features = [range(0,256),range(0,256),range(0,256),range(0,256),range(0,256),range(0,256)]
    masks = getMasksFromPoster(gPoster)
    
    # Assemble the regions Dictionary by putting in the data for every region that exists in 
    # the poster
    for i in range(6): 
        
        smoo = dat.smoothed(histos[i])
        if Image[gPoster==graylevels[i]].size != 0:
            # Calculate the maximum, minimum, mean pixel value of the region
            MAX = np.max(Image[gPoster==graylevels[i]])
            MIN = np.min(Image[gPoster==graylevels[i]])
            MEAN = int(np.mean(Image[gPoster==graylevels[i]]))
            # Determine the peak pixel value of the molybdenum in the region and produce
            # a histogram of the region with findMo in the histograms module
            MoPEAK,histo = hist.findMoPeakByImg(Image[gPoster==graylevels[i]],returnHist=True)
            # Get all peaks and valleys in the regions histogram
            PEAKS,Y = dat.getMaxima(smoo, smoonum=6)
            VALLEYS,Y = dat.getMinima(smoo, smoonum=6)
            # Get all inflection points in the Histogram
            NEGINFL,Y = dat.getInflectionPoints(smoo, smoonum=6,sign = 'negative')
            POSINFL,Y = dat.getInflectionPoints(smoo, smoonum=6,sign = 'positive')
            
            # Convert all lists into numpy ndarrays, which make it easier to use these
            # values in the future
            PEAKS = np.asarray(PEAKS).astype(np.uint8)
            VALLEYS = np.asarray(VALLEYS).astype(np.uint8)
            NEGINFL = np.asarray(NEGINFL).astype(np.uint8)
            POSINFL = np.asarray(POSINFL).astype(np.uint8)
            
            # Assemble the subdictionary for this region and add it to the regions 
            # dictionary. 
            regions[labels[i]] = {
            'RegMask':masks[i],'GrayLevel':graylevels[i],
            'Histogram':histos[i],
            'Max':MAX,'Min':MIN,
            'Mean':MEAN,'MoPeak':MoPEAK,
            'Peaks':PEAKS,'Valleys':VALLEYS,
            'NegInfl':NEGINFL,'PosInfl':POSINFL}
        else:
            # if no pixels are labeled as part of a particular region, the value of that 
            # region in the regions dictionary is 'Null'.
            regions[labels[i]] = 'Null'
        
    return regions
    
###################################################################################

###################################################################################

def applyPtThresh(image, PtThresh, regionMask=0, Mask=0):
    """
    Applies the platinum threshold to an image. 
    """
    PtMap = image.copy()
    if type(Mask)==np.ndarray:
        PtMap[Mask==0]=0         # Apply the Mask. Masked areas are in white.
    if type(regionMask)==np.ndarray:
        PtMap[regionMask==0]=0 # Isolate the current region. Mask off rest in white
    PtMap = binops.threshold(PtMap,PtThresh) # Apply the threshold
    
    return PtMap
    
###################################################################################

###################################################################################

def applyDirtThresh(image, DirtThresh, regionMask=0, Mask=0, kernSize=2):
    """
    Applies the dirt threshold to an image and then performs a morphological 
    opening to the thresholded image. 
    """
    DirtMap = image.astype(np.uint8)  # Make a copy of the original image
    if type(Mask)==np.ndarray:
        DirtMap[Mask==0]=255         # Apply the Mask. Masked areas are in white.
    if type(regionMask)==np.ndarray:
        DirtMap[regionMask==0]=255 # Isolate the current region. Mask off rest in white
    DirtMap = binops.threshold(DirtMap,0,DirtThresh) # Apply the threshold
    DirtKernel = fun.makeDiamondKernel(kernSize) # Create morphological kernel
    DirtMap = cv2.morphologyEx(DirtMap, cv2.MORPH_OPEN,DirtKernel) # Apply morph opening step
    return DirtMap
    
###################################################################################

###################################################################################

def getMolyMap(DirtMap, PtMap, regionMask=0, Mask=0):
    """
    Gets the map of the molybdenum given designated masks of the Dirt, Platinum,
    region, and Mask. 
    """
    MolyMap = np.ones(DirtMap.shape)
    MolyMap[DirtMap!=0]=0
    MolyMap[PtMap!=0]=0
    if type(Mask)==np.ndarray:
        MolyMap[Mask==0]=0         # Apply the Mask. Masked areas are in white.
    if type(regionMask)==np.ndarray:
        MolyMap[regionMask==0]=0 # Isolate the current region. Mask off rest in white    
    return MolyMap

###################################################################################

###################################################################################

def getMasksFromPoster(poster):
    """
    Receives a poster of an imagea and returns a list of images in which pixels 
    in the region have a value of 1 and pixels not in the region have a value of
    0. The exception is the 'blk' region, which is reversed. 
    """
    # Create the images
    blk = poster.copy()
    pleat = poster.copy()
    darkMo = poster.copy()
    Mo = poster.copy()
    highEx = poster.copy()
    Plat = poster.copy()
    # isolate various sections
    blk[blk!=0]=255
    pleat[pleat!=50]=0
    darkMo[darkMo!=85]=0
    Mo[Mo!=150]=0
    highEx[highEx!=200]=0
    Plat[Plat!=255]=0
    # Make masks of the regions where
    pleatMask = pleat/50
    darkMoMask = darkMo/85
    MoMask = Mo/150
    highExMask = highEx/200
    PlatMask = Plat/255

    masks = [blk,pleatMask,darkMoMask,MoMask,highExMask,PlatMask]

    return masks
    
###################################################################################

###################################################################################

def bigMaskEdges(image,res, maxFeatureSize=2000, Bkgrdthreshold = 95,verbose=False):
    """
    Creates a mask for masking off the edges of a large foil scan.
        Inputs:
         - image - image to be masked
        Key-word Arguments:
         - maxFeatureSize - largest feature diameter not considered to be the 
            edge of the foil. Default set to 10000 microns. 
         - threshold - approximate maximum value of the background
    """
    # want to reduce image to an image with a height of 1 mm
    rszheight = int(1000/np.sqrt(res)) 
    
    rszfactor = float(rszheight)/float(image.shape[0])
    resized = misc.imresize(image, rszfactor, interp='bilinear')
    scaledMaxFeat = int(rszfactor*maxFeatureSize/np.sqrt(res))
    threshed = resized.astype(np.uint8)
    threshed[threshed<=Bkgrdthreshold] = 0
    threshed[threshed>Bkgrdthreshold] = 1
    if verbose:
        print "Resize height: " + str(rszheight)
        print "Resize factor: " + str(rszfactor)
        print "Resize shape: " + str(resized.shape)
        print "Kernel width: " + str(scaledMaxFeat)

    kernel = np.ones((scaledMaxFeat,scaledMaxFeat))
    removeDirt = cv2.morphologyEx(threshed, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    floodSeed = np.bitwise_not(removeDirt.astype(np.bool_))
    floodSeed[1:-1,1:-1]=False
    Edgeonly = binops.floodBySeed(removeDirt,floodSeed,0,1,0,growthMin = 0, growthMax=100000)
    Edgeonly = np.bitwise_not(Edgeonly).astype(np.uint8)
    #Edgeonly = cv2.morphologyEx(threshed, cv2.MORPH_OPEN, kernel, iterations=1)
    kernel2 = np.ones((scaledMaxFeat/2,scaledMaxFeat/2))
    Edgeonly = cv2.morphologyEx(Edgeonly, cv2.MORPH_ERODE, kernel2)
    EdgeMask = misc.imresize(Edgeonly,image.shape,interp='bilinear')
    #EdgeMask=EdgeMask.astype(image.dtype)
    return EdgeMask

###################################################################################

###################################################################################

def FilterFeatures(sectData):
    """
    FilterFeatures makes sure that any features (i.e. a Peak, an inflection point,
    or a valley) in an image Histogram that are identified by a function are not 
    greater than the maximum pixel value or less than the minimum pixel value.
    """
    # statFeats are integers or single values, listFeats are feats that are lists
    statFeats = {k:sectData[k] for k in ['Max','Min','Mean','MoPeak']}
    listFeats = {k:sectData[k] for k in ['Peaks','NegInfl','PosInfl','Valleys']}
    
    for i in listFeats:
        for j in listFeats[i]:
            # if one of the features is greater than the Maximum or less than
            # the Minimum, eliminate that feature.
            if statFeats['Max'] <= j >= statFeats['Max']:
                listFeats[i]=listFeats[i][listFeats[i]!=j]
                
    statFeats.update(listFeats)
    ret = sectData.copy()
    ret.update(statFeats)#<-------------------------#####################
    return ret
    

    