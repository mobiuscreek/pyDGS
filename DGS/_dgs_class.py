# encoding: utf-8
"""
pyDGS - a Python framework for wavelet-based digital grain size analysis

pyDGS is an open-source project dedicated to provide a Python framework to compute estimates of grain size distribution  using the continuous wavelet transform method of Buscombe (2013) from an image of sediment where grains are clearly resolved. DOES NOT REQUIRE CALIBRATION

This program implements the algorithm of:

Buscombe, D. (2013) Transferable Wavelet Method for Grain-Size Distribution from Images of Sediment Surfaces and Thin Sections, and Other Natural Granular Patterns. Sedimentology 60, 1709-1732

http://dbuscombe-usgs.github.io/docs/Buscombe2013_Sedimentology_sed12049.pdf

 Author:  Daniel Buscombe
           Grand Canyon Monitoring and Research Center
           United States Geological Survey
           Flagstaff, AZ 86001
           dbuscombe@usgs.gov
 First Revision January 18 2013   

For more information visit https://github.com/dbuscombe-usgs/pyDGS

:install:
    python setup.py install
    sudo python setup.py install
    pip install pyDGS
    
:test:
    python -c "import DGS; DGS.test.dotest()"

    python
    import DGS
    density = 10 # process every 10 lines
    res = 0.01 # mm/pixel
    doplot = 0 # don't make plots
    image_folder = '/home/sed_images'
    DGS.dgs(image_folder,density,doplot,res)

 REQUIRED INPUTS:
 folder e.g. '/home/my_sediment_images'
 if 'pwd', then the present directory is analysed

 OPTIONAL INPUTS [default values]
 density = process every density lines of image [10]
 doplot = 0=no, 1=yes [0]
 resolution = spatial resolution of image in mm/pixel [1]

Note that the larger the density parameter, the longer the execution time. 

:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
    
    This software is in the public domain because it contains materials that
    originally came from the United States Geological Survey, an agency of the
    United States Department of Interior. For more information, 
    see the official USGS copyright policy at
    http://www.usgs.gov/visual-id/credit_usgs.html#copyright
    Any use of trade, product, or firm names is for descriptive purposes only 
    and does not imply endorsement by the U.S. government.
    
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as mpl
import sys, getopt, os, glob
from PIL import Image
import csv

import cwt
import sgolay

__all__ = [
    'dgs',
    'get_me',
    ]

# =========================================================
def iseven(n):
   """Return true if n is even."""
   return n%2==0

# =========================================================
def isodd(n):
   """Return true if n is odd."""   
   return not iseven(n)

# =========================================================
def rescale(dat,mn,mx):
    """
    rescales an input dat between mn and mx
    """
    m = min(dat.flatten())
    M = max(dat.flatten())
    return (mx-mn)*(dat-m)/(M-m)+mn
    
# =========================================================
def ascol( arr ):
    '''
    reshapes row matrix to be a column matrix (N,1).
    '''
    if len( arr.shape ) == 1: arr = arr.reshape( ( arr.shape[0], 1 ) )
    return arr    

# =========================================================
def writeout( outfolder, item, sz, pdf ):
    (dirName, fileName) = os.path.split(item)
    (fileBaseName, fileExtension)=os.path.splitext(fileName)
    
    with open(outfolder+os.sep+fileBaseName+'_psd.txt', 'w') as f:
       np.savetxt(f, np.hstack((ascol(sz),ascol(pdf))), delimiter=', ', fmt='%s')   
    print 'psd results saved to '+outfolder+os.sep+fileBaseName+'_psd.txt'

# =========================================================
# =========================================================
def dgs(folder, density, doplot, resolution):

   print "==========================================="
   print "======DIGITAL GRAIN SIZE: WAVELET=========="
   print "==========================================="
   print "=CALCULATE GRAIN SIZE-DISTRIBUTION FROM AN="
   print "====IMAGE OF SEDIMENT/GRANULAR MATERIAL===="
   print "==========================================="
   print "======A PROGRAM BY DANIEL BUSCOMBE========="
   print "========USGS, FLAGSTAFF, ARIZONA==========="
   print "=========REVISION 2.5, NOV 2014============"
   print "==========================================="

   # exit program if no input folder given
   if not folder:
      print 'A folder is required!!!!!!'
      sys.exit(2)

   # print given arguments to screen and convert data type where necessary
   if folder:
      print 'Input folder is ', folder
   if density:
      density = np.asarray(density,int)
      print 'Every '+str(density)+' rows will be processed'
   if doplot:
      doplot = np.asarray(doplot,int)
      print 'Doplot is '+str(doplot)
   if resolution:
      resolution = np.asarray(resolution,float)
      print 'Resolution is '+str(resolution)

   if not density:
      density = 10
      print '[Default] Density is '+str(density)

   if not doplot:
      doplot = 0
      print '[Default] No plot will be produced. To change this, set doplot to 1'

   if not resolution:
      resolution = 1
      print '[Default] Resolution is '+str(resolution)+' mm/pixel'

   # special case = pwd
   if folder=='pwd':
      folder = os.getcwd()

   if folder[-1]!=os.sep:
      folder = folder + os.sep   

   ## if make plot
   #if doplot:
   # if directory does not exist
   if os.path.isdir(folder+"DGS_outputs")==False:
      # create it
      try:
         os.mkdir(folder+os.sep+"DGS_outputs")
         outfolder = folder+os.sep+"DGS_outputs" 
      except:
         outfolder = os.getcwd()+os.sep+"DGS_outputs"
         if os.path.isdir(outfolder)==False:
            os.mkdir(outfolder)                              
                  
   maxscale = 8
   notes = 8

   # cover all major file types
   files1 = glob.glob(folder+os.sep+"*.JPG")
   files2 = glob.glob(folder+os.sep+"*.jpg")
   files3 = glob.glob(folder+os.sep+"*.jpeg")
   files4 = glob.glob(folder+os.sep+"*.TIF")
   files5 = glob.glob(folder+os.sep+"*.tif")
   files6 = glob.glob(folder+os.sep+"*.TIFF")
   files7 = glob.glob(folder+os.sep+"*.tiff")
   files8 = glob.glob(folder+os.sep+"*.PNG")
   files9 = glob.glob(folder+os.sep+"*.png")

   files = files1+files2+files3+files4+files5+files6+files7+files8+files9

   csvfilename = outfolder+os.sep+'dgs_results.csv'
   f_csv = open(csvfilename, 'ab')
   csvwriter = csv.writer(f_csv, delimiter=',')
   csvwriter.writerow(['Image', 'mean','sorting','skewness','kurtosis', 'maxscale', 'notes', 'density', 'resolution', 'p=.05', 'p=.1', 'p=.16', 'p=.25', 'p=.5', 'p=.75', 'p=.84', 'p=.9', 'p=.95'])

   for item in files:
   
      print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
      print "Processing image %s" % (item)   
      try:
          im = Image.open(item).convert("L")
      except IOError:
          print 'cannot open', item
          sys.exit(2)
    
      # convert to numpy array
      region = np.array(im)
      nx, ny = np.shape(region)
      mn = min(nx,ny)

      if isodd(mn/4):
           window_size = (mn/4)
      else:
           window_size = (mn/4)-1

      try:
         Zf = sgolay.sgolay2d( region, window_size, order=3)
      except:
         Zf = sgolay.sgolay2d( region, window_size+1, order=3)     

      # rescale filtered image to full 8-bit range
      useregion = rescale(region-Zf.getdata(),0,255)
      del Zf

      mult = (1/notes)*int(float(100*(1/np.std(region.flatten()))))

      #dat = cwt.Cwt(np.asarray(useregion,'int8'), maxscale, notes, density, mult)
      #d = dat.getvar()
      #scales = (np.pi/2)*dat.getscales()
      
      d, scales = get_me(useregion, maxscale, notes, density, mult)

      index = np.nonzero(scales<ny/5)
      scales = scales[index]
      d = d[index]
      d = d/np.sum(d)
     
      n = np.r_[0:len(scales)]-(len(scales)-1)/2
      d = d*np.exp(-(0.5)*((np.pi/2)*n/((len(scales)-1)/2))**2)
      d = d/np.sum(d)   

      # get real scales by multiplying by resolution (mm/pixel)
      scales = scales*resolution

      writeout( outfolder, item, scales, d )

      mnsz = np.sum(d*scales)
      print "mean size = ", mnsz 

      srt = np.sqrt(np.sum(d*((scales-mnsz)**2)))
      print "stdev = ",srt 

      sk = (sum(d*((scales-mnsz)**3)))/(100*srt**3)
      print "skewness = ",sk

      kurt = (sum(d*((scales-mnsz)**4)))/(100*srt**4)
      print "kurtosis = ",kurt

      pd = np.interp([.05,.1,.16,.25,.5,.75,.84,.9,.95],np.hstack((0,np.cumsum(d))), np.hstack((0,scales)) )

      csvwriter.writerow([item, mnsz, srt, sk, kurt, maxscale, notes, density, resolution] + pd.tolist() )

      if doplot:
         fig = mpl.figure(1)
         fig.subplots_adjust(wspace = 0.3, hspace=0.3)
         mpl.subplot(221)
         Mim = mpl.imshow(im,cmap=mpl.cm.gray)

         mpl.subplot(222)
         Mim = mpl.imshow(region,cmap=mpl.cm.gray)

         showim = Image.fromarray(np.uint8(region))
         size = min(showim.size)
         originX = int(np.round(showim.size[0] / 2 - size / 2))
         originY = int(np.round(showim.size[1] / 2 - size / 2))
         cropBox = (originX, originY, originX + np.asarray(mnsz*5,dtype='int'), originY + np.asarray(mnsz*5,dtype='int'))
         showim = showim.crop(cropBox)

         mpl.subplot(223)
         Mim = mpl.imshow(showim,cmap=mpl.cm.gray)
         mpl.plot([np.shape(showim)[0]/3, np.shape(showim)[0]/3] , [np.shape(showim)[0]/3, np.shape(showim)[0]/3 + mnsz],'r' )
         mpl.axis('tight')

         mpl.subplot(224)
         mpl.ylabel('Proportion')
         mpl.xlabel('Size')
         mpl.plot(scales,d,'g-')

         (dirName, fileName) = os.path.split(item)
         (fileBaseName, fileExtension)=os.path.splitext(fileName)

         mpl.savefig(outfolder+os.sep+fileBaseName+'_res.png')
         mpl.close()

   f_csv.close()
      
   x = []; y = []
   for item in files:
      (dirName, fileName) = os.path.split(item)
      (fileBaseName, fileExtension)=os.path.splitext(fileName)
      tmp = outfolder+os.sep+fileBaseName+'_psd.txt'
      x.append(np.genfromtxt(tmp, delimiter=',', usecols=0))
      y.append(np.genfromtxt(tmp, delimiter=',', usecols=1))
      
   try:
      xi = np.linspace(np.min(x),np.max(x),np.shape(x)[1])   
   except: # non-uniform x
      xi = np.linspace(np.min(np.hstack(x)),np.max(np.hstack(x)),len(np.hstack(x))) 
   yi = np.interp(xi,np.hstack(x),np.hstack(y))
   yi = yi/np.sum(yi)   

   with open(outfolder+os.sep+'merged_psd.txt', 'w') as f:
      np.savetxt(f, np.hstack((ascol(xi),ascol(yi))), delimiter=', ', fmt='%s')   
   print 'psd results saved to '+outfolder+os.sep+'merged_psd.txt'

   csvfilename = outfolder+os.sep+'dgs_results_merged.csv'
   f_csv = open(csvfilename, 'ab')
   csvwriter = csv.writer(f_csv, delimiter=',')
   csvwriter.writerow(['Image', 'mean','sorting','skewness','kurtosis', 'maxscale', 'notes', 'density', 'resolution', 'p=.05', 'p=.1', 'p=.16', 'p=.25', 'p=.5', 'p=.75', 'p=.84', 'p=.9', 'p=.95'])

   mnsz = np.sum(yi*xi)
   print "merged mean size = ", mnsz 

   srt = np.sqrt(np.sum(yi*((xi-mnsz)**2)))
   print "merged stdev = ",srt 

   sk = (sum(yi*((xi-mnsz)**3)))/(100*srt**3)
   print "merged skewness = ",sk

   kurt = (sum(yi*((xi-mnsz)**4)))/(100*srt**4)
   print "merged kurtosis = ",kurt

   pd = np.interp([.05,.1,.16,.25,.5,.75,.84,.9,.95],np.hstack((0,np.cumsum(yi))), np.hstack((0,xi)) )

   csvwriter.writerow([item, mnsz, srt, sk, kurt, maxscale, notes, density, resolution] + pd.tolist() )
   f_csv.close()

# =========================================================
def get_me(useregion, maxscale, notes, density, mult):
   dat = cwt.Cwt(np.asarray(useregion,'int8'), maxscale, notes, density, mult)
   return dat.getvar(), (np.pi/2)*dat.getscales()

