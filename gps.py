"""
Greg Starr
this is based mostly on Bill Rideout's tec.py
scripts, I'm not using classes and I am using
numpy because I like it better, the rinex
reading was made by Michael Hirsch and Greg Starr
"""
from __future__ import division,absolute_import,print_function
import numpy as np
from datetime import datetime
from pandas import DataFrame,Series,Panel4D
from pandas.io.pytables import read_hdf
from os.path import splitext,expanduser,getsize
from io import BytesIO
import time
from pymap3d.coordconv3d import ecef2geodetic,ecef2aer,aer2geodetic


f1 = 1575.42E6 #MHz
f2 = 1227.6E6  #MHz
def getRanges(data,svn,maxgap=3,maxjump=1.0): 
    if c2p2(data,svn):
        nans = np.logical_or.reduce((np.isnan(data[['L1','L2','C1','C2'],svn,:,'data']).T))
    else:
        nans = np.logical_or.reduce((np.isnan(data[['L1','L2','C1','P2'],svn,:,'data']).T))
    inarc=False
    start=[]
    end=[]
    phase=2.85E9*(data['L1',svn,:,'data']/f1-data['L2',svn,:,'data']/f2)
    lgi=0
    for i in range(len(nans)):
        if inarc:
            if nans[i]:
                if i-lgi>maxgap:
                    inarc=False
                    end.append(lgi)
            else:
                if abs(phase[i]-phase[lgi])>maxjump:
                    end.append(lgi)
                    start.append(i)
                lgi=i

        else:
            if not nans[i]:
                inarc=True
                start.append(i)
                lgi=i
    if len(start)!=len(end): end.append(i)
    ranges = [(data.major_axis[a],data.major_axis[b]) for a,b in zip(start,end)]

    return ranges
    
def getIntervals(data,svn,maxgap=3,maxjump=1.2):
    if c2p2(data,svn):
        fin = np.where(np.logical_and.reduce((
                       np.isfinite(data[['L1','L2','C1','C2'],svn,:,'data']).T)))[0]
    else:
        fin = np.where(np.logical_and.reduce((
                       np.isfinite(data[['L1','L2','C1','P2'],svn,:,'data']).T)))[0]
    ranges=[]
    if len(fin)==0:
        return ranges
    phase=2.85E9*(data['L1',svn,:,'data']/f1-data['L2',svn,:,'data']/f2)
    b=fin[0]
    last=fin[0]
    for i in fin[1:]:
        if i-last>maxgap or abs(phase[i]-phase[last])>maxjump:
            ranges.append((b,last))
            b=i
        last=i
        if i==fin[-1]:
            ranges.append((b,last))
    ranges=[(data.major_axis[a[0]],data.major_axis[a[1]]) for a in ranges]
    return ranges
        

def getTec(data,svn,drange,satbias=None):
    if c2p2(data,svn,drange):
        diffrange = (2.85E9/3.0E8)*(
            data['C2',svn,drange[0]:drange[1],'data']
            -data['C1',svn,drange[0]:drange[1],'data'])
    else:
        diffrange = (2.85E9/3.0E8)*(
            data['P2',svn,drange[0]:drange[1],'data']
            -data['C1',svn,drange[0]:drange[1],'data'])
        
    phase=2.85E9*(data['L1',svn,drange[0]:drange[1],'data']/f1
                  -data['L2',svn,drange[0]:drange[1],'data']/f2)        
        
    difflist = np.array(sorted(phase-diffrange))
    difflist = difflist[np.isfinite(difflist)]
    mediandiff = difflist[int(len(difflist)/2)]
    distwidth = difflist[int(len(difflist)*.75)]-difflist[int(len(difflist)*.25)]
    medianerr = distwidth/np.sqrt(len(difflist))
    tec = phase - mediandiff

    return tec,medianerr


def c2p2(data,svn,drange=(None,None)):
    return (np.sum(~np.isnan(
        data['C2',svn,drange[0]:drange[1],'data']))>
            np.sum(~np.isnan(
                data['P2',svn,drange[0]:drange[1],'data'])))

###############
#Shouldn't work
###############
def c2p2alt(data,site,drange=(None,None)):
    return (np.sum(~np.isnan(
        data[site,drange[0]:drange[1],'C2','data']))>
            np.sum(~np.isnan(
                data[site,drange[0]:drange[1],'P2','data'])))
###############
def getTecalt(data,site,drange,satbias=None):
    if c2p2alt(data,site,drange):
        diffRange = (2.85E9/3.0E8)*(
            data[site,drange[0]:drange[1],'C2','data']
            -data[site,drange[0]:drange[1],'C1','data'])
    else:
        diffRange = (2.85E9/3.0E8)*(
            data[site,drange[0]:drange[1],'P2','data']
            -data[site,drange[0]:drange[1],'C1','data'])
        
    phase=2.85E9*(data[site,drange[0]:drange[1],'L1','data']/f1
                  -data[site,drange[0]:drange[1],'L2','data']/f2)        
        
    diffList = sorted(phase-diffRange)
    medianDiff = diffList[int(len(diffList)/2)]
    distWidth = diffList[int(len(diffList)*.75)]-diffList[int(len(diffList)*.25)]
    medianErr = distWidth/np.sqrt(len(diffList))
    tec = phase - medianDiff
    if satbias!=None:
        tec-=satbias
    return tec,medianErr
####################
def getRangesalt(data,site,maxgap=3,maxjump=2.0): 
    if c2p2alt(data,site):
        nans = np.logical_or.reduce((np.isnan(data[site,:,'L1','data']),
                                     np.isnan(data[site,:,'L2','data']),
                                     np.isnan(data[site,:,'C1','data']),
                                     np.isnan(data[site,:,'C2','data'])))
    else:
        nans = np.logical_or.reduce((np.isnan(data[site,:,'L1','data']),
                                     np.isnan(data[site,:,'L2','data']),
                                     np.isnan(data[site,:,'C1','data']),
                                     np.isnan(data[site,:,'P2','data'])))
    inarc=False
    start=[]
    end=[]
    phase=2.85E9*(data[site,:,'L1','data']/f1-data[site,:,'L2','data']/f2)
    lgi=0

    for i in range(len(nans)):
        if inarc:
            if nans[i]:
                if i-lgi>maxgap:
                    inarc=False
                    end.append(lgi)
            else:
                if abs(phase[i]-phase[lgi])>maxjump:
                    end.append(lgi)
                    start.append(i)
                lgi=i

        else:
            if not nans[i]:
                inarc=True
                start.append(i)
                lgi=i
    
    if len(start)!=len(end): end.append(i)
    ranges = [(data.items[a],data.items[b]) for a,b in zip(start,end)]

    return ranges
####################


class satelliteBias:
    """satelliteBias is a class to get satellite biases in tec units
    Once biases are loaded, get them using the dictionary attribute
    dict.  Key is tuple of prn (integer) and biasType (integer).  If
    TEC is calculated using C1, set biasType to 1.  If
    TEC is calculated using P1, set biasType to 0. If TEC is calculated
    using C1 and C2, set biasType to 2.
    """

    def __init__(self, satFile, C1BiasFile, L2C2BiasFile):
        """__init__ sets up the dictionary self.dict
        satFile - the ionex file with satellite biases as produced by
            JPL in ftp://cddis.gsfc.nasa.gov/pub/gps/products/ionex/
        C1BiasFile - the P1C1 bias file (may be None for verification only)
        L2C2BiasFile - the P2C2 bias file (may be None for verification only)
        """
        self.dict = {}
        self.__parseSatBiasFile(satFile)
        self.__parseC1BiasFile(C1BiasFile)
        self._parseC2BiasFile(L2C2BiasFile)


    def __parseSatBiasFile(self, satFile):
        """__parseSatBiasFile parses satellite bias file, and adds data
        to self.dict
        """
        indicatorStr = 'DIFFERENTIAL CODE BIASES'
        # conversionFactor in TECu
        conversionFactor = -0.463*6.158 # diff ns -> meters -> tec
        f = open(satFile)
        lines = f.readlines()
        f.close()
        lineFound = 0 # indicates right line found
        dataFound = 0 # indicates at least one line of data found
        for line in lines:
            if line[0:len(indicatorStr)] == indicatorStr:
                lineFound = 1
                continue
            if lineFound:
                items = line.split()
                # see if we're done
                try:
                    try:
                        sv = int(items[0])
                    except:
                        # see if last two characters are ints and first is G
                        if items[0][0] == 'G':
                            sv = int(items[0][-2:])
                        else:
                            raise(IOError, '')
                    bias = float(items[1])*conversionFactor
                    dataFound = 1
                    # add this data to dict
                    self.dict[(sv,0)] = bias
                except:
                    if dataFound == 0:
                        # no valid lines found
                        raise(IOError,
                              'No valid data found after indicator in %s'
                              % (satFile))
                    else:
                        return
        # if we got here, the indicator wasn't found, or the data was the last line in the file
        if dataFound == 1:
            return
        else:
            raise(IOError,
                  'No indicator string found in %s' % (satFile))

    def __parseC1BiasFile(self, C1BiasFile):
        """__parseC1BiasFile parses p1c1 bias file, and adds data
        to self.dict
        Bias is added to existing biases
        """
        conversionFactor = -0.463*6.158 # diff ns -> meters -> tec
        # allow no C1BiasFile for case where normal bias just being verified
        if (C1BiasFile == None):
            return
        f = open(C1BiasFile)
        lines = f.readlines()
        f.close()
        # print warning if no data found
        dataFound = False
        for line in lines:
            try:
                items = line.split()
                if items[0][0] in ('G', 'g'):
                    prn = int(items[0][1:])
                else:
                    prn = int(items[0])
                addBias =  float(items[1])* conversionFactor
                self.dict[(prn, 1)] =  self.dict[(prn, 0)] - addBias
                dataFound = True
            except:
                continue
        if not dataFound:
            print('WARNING: No valid data found in %s' % (C1BiasFile))

    def _parseC2BiasFile(self, L2C2BiasFile):
        """__parseC2BiasFile parses p2c2 bias file, and adds data
        to self.dict
        Bias is added to existing biases
        """
        conversionFactor = -0.463*6.158 # diff ns -> meters -> tec
        # allow no C1BiasFile for case where normal bias just being verified
        if (L2C2BiasFile == None):
            return
        f = open(L2C2BiasFile)
        lines = f.readlines()
        f.close()
        # print warning if no data found
        dataFound = False
        for line in lines:
            try:
                items = line.split()
                if items[0][0] in ('G', 'g'):
                    prn = int(items[0][1:])
                else:
                    prn = int(items[0])
                addBias =  float(items[1])* conversionFactor
                self.dict[(prn, 2)] =  self.dict[(prn, 1)] + addBias
                dataFound = True
            except:
                continue
        if not dataFound:
            print('WARNING: No valid data found in %s' % (L2C2BiasFile))


def rinexobs(rinexfile,h5file=None,returnHead=False,writeh5=False):
    
    #open file, get header info, possibly speed up reading data with a premade h5 file
    stem,ext = splitext(expanduser(rinexfile))
    with open(rinexfile,'r') as f:
        t=time.time()
        lines = f.read().splitlines(True)
        lines.append('')
        header,version,headlines,obstimes,sats,svset = scan(lines)
        print('{} is a RINEX {} file, {} kB.'.format(rinexfile,version,getsize(rinexfile)/1000.0))
        if h5file==None:
            data = processBlocks(lines,header,obstimes,svset,headlines,sats)
        else:
            data = read_hdf(h5file,key='data')
        print("finished in {0:.2f} seconds".format(time.time()-t))
        
    #write an h5 file if specified
    if writeh5:
        h5fn = stem + '.h5'
        print('saving OBS data to {}'.format(h5fn))
        data.to_hdf(h5fn,key='data',mode='w',format='table')
        
    #return info including header if desired
    if returnHead:
        return header,data
    else:
        return data


# this will scan the document for the header info and for the line on
# which each block starts
def scan(lines):
    header={}        
    eoh=0
    for i,line in enumerate(lines):
        if "END OF HEADER" in line:
            eoh=i
            break
        if line[60:].strip() not in header:
            header[line[60:].strip()] = line[:60].strip()
        else:
            header[line[60:].strip()] += " "+line[:60].strip()
    verRinex = float(header['RINEX VERSION / TYPE'].split()[0])
    header['APPROX POSITION XYZ'] = [float(i) for i in header['APPROX POSITION XYZ'].split()]
    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
    header['# / TYPES OF OBSERV'][0] = int(header['# / TYPES OF OBSERV'][0])
    header['INTERVAL'] = float(header['INTERVAL'])
        
    headlines=[]
    obstimes=[]
    sats=[]
    svset=set()
    i=eoh+1
    while True:
        if not lines[i]: break
        if not int(lines[i][28]):
            #no flag or flag=0
            headlines.append(i)
            obstimes.append(_obstime([lines[i][1:3],lines[i][4:6],
                                   lines[i][7:9],lines[i][10:12],
                                   lines[i][13:15],lines[i][16:26]]))
            numsvs = int(lines[i][30:32])
            if(numsvs>12):
                sp=[]
                for s in range(numsvs):
                    sp.append(int(lines[i][33+(s%12)*3:35+(s%12)*3]))
                    if s==12: i+= 1
                sats.append(sp)
            else:
                sats.append([int(lines[i][33+s*3:35+s*3]) for s in range(numsvs)])
        
            i+=numsvs*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))+1
        else:
            #there was a comment or some header info
            flag=int(lines[i][28])
            if(flag!=4):
                print(flag)
            skip=int(lines[i][30:32])
            i+=skip+1
    for sv in sats:
        svset = svset.union(set(sv))

    return header,verRinex,headlines,obstimes,sats,svset



def processBlocks(lines,header,obstimes,svset,headlines,sats):
    
    obstypes = header['# / TYPES OF OBSERV'][1:]
    blocks = np.nan*np.ones((len(obstypes),max(svset)+1,len(obstimes),3))
    
    for i in range(len(headlines)):
        linesinblock = len(sats[i])*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))
        block = ''.join(lines[headlines[i]+1:headlines[i]+linesinblock+1])
        bdf = _block2df(block,obstypes,sats[i],len(sats[i]))
        blocks[:,np.asarray(sats[i],int),i,:] = bdf
        
    blocks = Panel4D(blocks,
                     labels=obstypes,
                     items=np.arange(max(svset)+1),
                     major_axis=obstimes,
                     minor_axis=['data','lli','ssi'])
    blocks = blocks[:,list(svset),:,:]
    
    return blocks       
        

def _obstime(fol):
    year = int(fol[0])
    if 80<= year <=99:
        year+=1900
    elif year<80: #because we might pass in four-digit year
        year+=2000
    return datetime(year=year, month=int(fol[1]), day= int(fol[2]),
                    hour= int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1) *100000
                    )

def _block2df(block,obstypes,svnames,svnum):
    """
    input: block of text corresponding to one time increment INTERVAL of RINEX file
    output: 2-D array of float64 data from block. Future: consider whether best to use Numpy, Pandas, or Xray.
    """
    nobs = len(obstypes)
    stride=3

    strio = BytesIO(block.encode())
    barr = np.genfromtxt(strio, delimiter=(14,1,1)*5).reshape((svnum,-1), order='C')

    data = barr[:,0:nobs*stride:stride]
    lli  = barr[:,1:nobs*stride:stride]
    ssi  = barr[:,2:nobs*stride:stride]

    data = np.vstack(([data],[lli],[ssi])).T

    return data


def readRinexNav(fn,writeh5=None):
    """
    Michael Hirsch
    It may actually be faster to read the entire file via f.read() and then .split()
    and asarray().reshape() to the final result, but I did it frame by frame.
    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    """
    stem,ext = splitext(expanduser(fn))
    startcol = 3 #column where numerical data starts
    nfloat=19 #number of text elements per float data number
    nline=7 #number of lines per record

    with open(expanduser(fn),'r') as f:
        #find end of header, which has non-constant length
        while True:
            if 'END OF HEADER' in f.readline(): break
        #handle frame by frame
        sv = []; epoch=[]; raws=''
        while True:
            headln = f.readline()
            if not headln: break
            #handle the header
            sv.append(headln[:2])
            year = int(headln[2:5])
            if 80<= year <=99:
                year+=1900
            elif year<80: #good till year 2180
                year+=2000
            epoch.append(datetime(year =year,
                                  month   =int(headln[5:8]),
                                  day     =int(headln[8:11]),
                                  hour    =int(headln[11:14]),
                                  minute  =int(headln[14:17]),
                                  second  =int(headln[17:20]),
                                  microsecond=int(headln[21])*100000))
            """
            now get the data.
            Use rstrip() to chomp newlines consistently on Windows and Python 2.7/3.4
            Specifically [:-1] doesn't work consistently as .rstrip() does here.
            """
            raw = (headln[22:].rstrip() +
                   ''.join(f.readline()[startcol:].rstrip() for _ in range(nline-1))
                   +f.readline()[startcol:40].rstrip())

            raws += raw + '\n'

    raws = raws.replace('D','E')

    strio = BytesIO(raws.encode())
    darr = np.genfromtxt(strio,delimiter=nfloat)

    nav= DataFrame(darr, epoch,
               ['SVclockBias','SVclockDrift','SVclockDriftRate','IODE',
                'Crs','DeltaN','M0','Cuc','Eccentricity','Cus','sqrtA','TimeEph',
                'Cic','OMEGA','CIS','Io','Crc','omega','OMEGA DOT','IDOT',
                'CodesL2','GPSWeek','L2Pflag','SVacc','SVhealth','TGD','IODC',
                'TransTime','FitIntvl'])
    nav['sv'] = Series(np.asarray(sv,int), index=nav.index)

    if writeh5:
        h5fn = stem + '.h5'
        print('saving NAV data to {}'.format(h5fn))
        nav.to_hdf(h5fn,key='NAV',mode='a',complevel=6,append=False)

    return nav

def getSatXYZ(nav,sv,times):
    
    """getSatelliteXYZ returns the satellite XYZ as a tuple at the inputted times
           inputs are rinex navigation data, satellite number, and list of times
        Output: tuple of satellite position in ECEF coordinates (X,Y,Z)
        Algorithm: Based on http://web.ics.purdue.edu/~ecalais/teaching/geodesy/EAS_591T_2003_lab_4.htm
        also based on Bill Rideout's tec.py
    """
    allSvInfo = nav[nav['sv']==sv] 
    timesarray = np.asarray(times,dtype='datetime64[ms]')
    navtimes = np.asarray(allSvInfo.index,dtype='datetime64[ms]')
    bestephind = np.array([np.argmin(abs(navtimes-t)) for t in timesarray])
    info = np.asarray(allSvInfo)[bestephind]
    info = DataFrame(info,index=times,columns=allSvInfo.columns)
    info['sv'] = sv
    info['gpstime'] = np.array([getGpsTime(t) for t in times])
    # constants
    GM = 3986005.0E8 # universal gravational constant
    OeDOT = 7.2921151467E-5
    
    #Basic Parameters
    t = info['gpstime']-info['TimeEph']
    mu = info['M0']+t*(np.sqrt(GM/info['sqrtA']**6)+info['DeltaN'])
    Ek = solveIter(mu,info['Eccentricity'])  
    Vk = np.asarray(np.arctan2(np.sqrt(1.0-info['Eccentricity'])*np.sin(Ek),
                               np.cos(Ek)-info['Eccentricity']),float)
    PhiK = Vk + info['omega']
    #Correct for orbital perturbations
    omega = np.asarray(info['omega']+info['Cus']*np.sin(2.0*PhiK)
             +info['Cuc']*np.cos(2.0*PhiK),float)
    r = np.asarray((info['sqrtA']**2)*(1.0-info['Eccentricity']*np.cos(Ek))
         +info['Crs']*np.sin(2.0*PhiK)+info['Crc']*np.cos(2.0*PhiK),float)
    i = np.asarray(info['Io']+info['IDOT']*t+info['CIS']*np.sin(2.0*PhiK)
         +info['Cic']*np.cos(2.0*PhiK),float)
    
    #Compute the right ascension
    Omega = np.asarray(info['OMEGA']+(info['OMEGA DOT']-OeDOT)*t-(OeDOT*info['TimeEph']),float)
    #Convert satellite position from orbital frame to ECEF frame
    cosOmega = np.cos(Omega)
    sinOmega = np.sin(Omega)
    cosomega = np.cos(omega)
    sinomega = np.sin(omega)
    cosi = np.cos(i)
    sini = np.sin(i)
    cosVk = np.cos(Vk)
    sinVk = np.sin(Vk)
    R11 = cosOmega*cosomega - sinOmega*sinomega*cosi
    R12 = -1.0*cosOmega*sinomega - sinOmega*cosomega*cosi
    #R13 = np.sin(Omega)*np.sin(i)
    R21 = sinOmega*cosomega + cosOmega*sinomega*cosi
    R22 = -1.0*sinOmega*sinomega + cosOmega*cosomega*cosi
    #R23 = -1.0*np.cos(Omega)*np.sin(i)
    R31 = sinomega*sini
    R32 = cosomega*sini
    #R33 = np.cos(i)
          
    xyz = np.zeros((len(times),3))
    rv = np.column_stack((r*cosVk,r*sinVk,np.zeros(r.shape)))
    
    R = np.empty((rv.shape[0],3,3))
    R[:,0,0] = R11
    R[:,0,1] = R12
    R[:,0,2] = 0
    R[:,1,0] = R21
    R[:,1,1] = R22
    R[:,1,2] = 0
    R[:,2,0] = R31
    R[:,2,1] = R32
    R[:,2,2] = 0
    
    #R = np.array([[R11[i],R12[i],0],
    #              [R21[i],R22[i],0],
    #              [R31[i],R32[i],0]])
    for i in range(len(times)): #THIS IS THE SLOWEST PART NOW
        xyz[i,:] = (R[i,:,:].dot(rv[i,:]))
        
    return xyz

def getGpsTime(dt):
    """_getGpsTime returns gps time (seconds since midnight Sat/Sun) for a datetime
    """
    total = 0
    days = (dt.weekday()+ 1) % 7 # this makes Sunday = 0, Monday = 1, etc.
    total += days*3600*24
    total += dt.hour * 3600
    total += dt.minute * 60
    total += dt.second
    return(total)

def solveIter(mu,e):
    """__solvIter returns an iterative solution for Ek
    Mk = Ek - e sin(Ek)
    adapted to accept vectors instead of single values
    from Bill Rideout's tec.py
    """
    thisStart = np.asarray(mu-1.01*e)
    thisEnd = np.asarray(mu + 1.01*e)
    bestGuess = np.zeros(mu.shape)

    for i in range(5): 
        minErr = 10000*np.ones(mu.shape)
        for j in range(5):
            thisGuess = thisStart + j*(thisEnd-thisStart)/10.0
            thisErr = np.asarray(abs(mu - thisGuess + e*np.sin(thisGuess)))
            mask = thisErr<minErr
            minErr[mask] = thisErr[mask]
            bestGuess[mask] = thisGuess[mask]
        
        # reset for next loop
        thisRange = thisEnd - thisStart
        thisStart = bestGuess - thisRange/10.0
        thisEnd = bestGuess + thisRange/10.0
        
    return(bestGuess)

def getZ(el):
    """getZ returns the mapping function given elevation in degrees and
       fitting parameter.
       Now fitting to equation:
                              1
           z =  ----------------------------
                sqrt(1.0 - (fit * cos(el))^2)
    """
    fit = 0.95
    term1 = 1 - (fit*np.cos(np.radians(el)))**2
    return 1.0 / np.sqrt(term1) 

def getZ2(el,recpos):
    """
             sqrt( [a+h+s]^2 - [a*cos(el)]^2 ) - sqrt( [a+h]^2 - [a*cos(el)]^2 )
    z(el) = ---------------------------------------------------------------------
                                          s
    a is height of observing station from earth center in km,
    h = 300km is height of ionosphere slab
    s = 200km is slab thickness
    """
    a = np.linalg.norm(recpos)/1000
    h=300
    s = 200
    Z = (np.sqrt((a+h+s)**2-(a*np.cos(np.radians(el[el>30])))**2) 
         -np.sqrt((a+h)**2-(a*np.cos(np.radians(el[el>30])))**2))/s
    
    return Z    


def minScalErr(stec,el,z,thisBias):
            
    intel=np.asarray(el[stec.index],int)
    sTEC=np.asarray(stec,float)
    zmap = z[stec.index]
    c=np.array([(i,np.average((sTEC[intel==i]-thisBias)
                              /zmap[intel==i])) for i in np.unique(intel) if i>30])
    
    return np.polyfit(c[:,0],c[:,1],1)[0]
     
def getPP(satpos,sv,recpos,pph,err=1.0):
    """
    get az and el to the satellite and repeatedly increase the range,
    converting to LLA each time to check the altitude. Stop when all
    the altitudes are within err of pph. Inputs satellite position 
    array in ECEF, satellite number, receiver position in ECEF, pierce point
    height in km and error if you want.
    """
    
    rlat,rlon,ralt = ecef2geodetic(recpos)
    sataz,satel,satr = ecef2aer(satpos[:,0],satpos[:,1],satpos[:,2],rlat,rlon,ralt)

    r=np.zeros(len(satr))
    pplat,pplon,ppalt = aer2geodetic(sataz,satel,r,rlat,rlon,ralt)
    mask = (ppalt/1000 - pph) < 0

    while np.sum(mask)>0:  
        r[mask]+=100
        pplat,pplon,ppalt = aer2geodetic(sataz,satel,r*1000,rlat,rlon,ralt)
        mask = (ppalt/1000 - pph) < 0
    
    sRange = r - 100.0
    eRange = r
    count = 0
    while not np.all(abs(ppalt/1000-pph)<err):
        count +=1
        mRange = (sRange + eRange) / 2.0
        pplat,pplon,ppalt = aer2geodetic(sataz,satel,mRange*1000,rlat,rlon,ralt)
        mask = ppalt/1000>pph
        eRange[mask] = mRange[mask]
        sRange[~mask] = mRange[~mask]
    
        if(count>100):
            raise TypeError('going too long')
            break
            
    ppalt = pph*1000
    
    return pplat,pplon,ppalt

def minScalBias(data,recpos):
    """
    This function calculates receiver bias via the minimum scalloping
    method. Inputs are the rinexobs head, rinexobs data, nav data, and a
    satellite bias object. Outputs the bias averaged from all satellites at
    all times in the rinexobs data
    """
    
    SvsUsed=0
    bias=0
    for sv in data.items:
        el = data['El',sv,:,'data'][~np.isnan(data['El',sv,:,'data'])]
        z = data['zmap',sv,:,'data'][~np.isnan(data['zmap',sv,:,'data'])]
        stec = data['TEC',sv,:,'data'][~np.isnan(data['TEC',sv,:,'data'])]
        if(len(np.unique(np.asarray(el[el>29],int)))<30): continue
        SvsUsed+=1

        #FIND SMALLEST ERROR AND WHICH BIAS CORRESPONDS TO IT
        err=np.zeros((10,))
        for i in range(10):
            err[i] = minScalErr(stec[abs(stec)<100],el,z,-50+i*10) #MAKE THE FILTERING MORE CUSTOMIZABLE
        startval=-50+np.argmin(abs(err))*10
        for i in range(10):
            err[i] = minScalErr(stec[abs(stec)<100],el,z,startval-5+i)
        startval+=np.argmin(abs(err))-5
        for i in range(10):
            err[i] = minScalErr(stec[abs(stec)<100],el,z,startval-.5+.1*i)
        bias += (np.argmin(abs(err))-5)*.1+startval
        
    return bias/SvsUsed

def GDfromRinex(rinexfile,navfile,satFile,C1BiasFile,h5file=None,writeh5=False,pph=350,satlist=None):
    
    head,data = rinexobs(rinexfile,returnHead=True,h5file=h5file,writeh5=writeh5)
    nav = readRinexNav(navfile)
    svBiasObj = satelliteBias(satFile,C1BiasFile,None)

    extra = np.nan*np.ones((14,data.shape[1],data.shape[2],data.shape[3]))
    recpos = np.asarray(head['APPROX POSITION XYZ'],float)[:,None]
    rlat,rlon,ralt = ecef2geodetic(recpos)

    print('sv',end=': ')
    for sv in data.items:
        print(sv,end=' ')
        if((sv,1) not in svBiasObj.dict): continue
        satbias = svBiasObj.dict[(sv,1)]

        #get time intervals, points where there is good tec
        ranges = getIntervals(data,sv)
        teclist = []
        timelist = []
        errlist=[]
        rbeg=[]
        pos=0
        for drange in ranges:
            rbeg.append(pos)
            tec,err = getTec(data,sv,drange)
            tec-=satbias
            teclist.append(tec)
            timelist.append(tec.index)
            errlist.append(err*np.ones(len(tec)))
            pos+=len(tec) 
            
        if len(teclist)==0 or len(timelist)==0:  
            continue
                        
        stec = Series(np.hstack((p for p in teclist)),index=np.hstack((t for t in timelist)))
        ntec = Series(np.hstack((j for j in errlist)),index=np.hstack((t for t in timelist)))
        for i,p in enumerate(rbeg):
            rbeg[i]-=np.sum(np.isnan(stec[:p]))
        rbeg=np.array(rbeg)
        ntec = ntec[~np.isnan(stec)]
        stec = stec[~np.isnan(stec)]
        
        satpos = getSatXYZ(nav,sv,stec.index)
        az,el,r = ecef2aer(satpos[:,0],satpos[:,1],satpos[:,2],rlat,rlon,ralt)
        satpossph = np.vstack([az,el,r/1000]).T 
        goodtimes = np.in1d(data.major_axis,stec.index) #times for satellite with data
        svi = list(data.items).index(sv) # matrix column corresponding to satellite
        extra[:3,svi,goodtimes,0] = satpos.T #XYZ
        extra[3:6,svi,goodtimes,0] = satpossph.T #Spherical
        extra[6,svi,goodtimes,0] = stec.values #TEC
        z = getZ(satpossph[:,1])
        extra[7,svi,goodtimes,0] = z #vertical mapping function
        pplat,pplon,ppalt = getPP(satpos,sv,recpos,pph) #Pierce Point
        extra[8,svi,goodtimes,0] = pplat
        extra[9,svi,goodtimes,0] = pplon
        extra[10,svi,goodtimes,0] = ppalt
        extra[11,svi,goodtimes,0] = ntec.values #err tec
        splittimes = np.where(goodtimes)[0][rbeg]
        extra[13,svi,splittimes,0] = 1
                
    data['X'] = extra[0]
    data['Y'] = extra[1]
    data['Z'] = extra[2]
    data['Az'] = extra[3]
    data['El'] = extra[4]
    data['R'] = extra[5]
    data['TEC'] = extra[6]
    data['zmap'] = extra[7]
    data['pplat'] = extra[8]
    data['pplon'] = extra[9]
    data['ppalt'] = extra[10]
    data['nTEC'] = extra[11]
    print()
    print('recbias',end=': ')
    recbias = minScalBias(data,recpos) #calculate receiver bias
    extra[6,:,:,0] -= recbias
    extra[12,:,:,0] = (extra[6,:,:,0])/extra[7,:,:,0] #vtec
    print(recbias)
    data['TEC'] = extra[6] #TEC adjusted with receiver bias
    data['vTEC'] = extra[12] #vTEC adjusted with receiver bias
    data['cslip'] = extra[13]
    
    d = {'TEC':[],'az2sat':[],'el2sat':[],'recBias':[],'satnum':[],
         'vTEC':[],'nTEC':[],'lol':[],'raw':[]}
    dataloc = []
    times = []
    if(satlist==None): satlist = data.items
    for sv in satlist:
        msk = np.isfinite(data['TEC',sv,:,'data']) #mask of times with data
        phase = 2.85E9*(data['L1',sv,:,'data']/f1-data['L2',sv,:,'data']/f2)
        d['raw'].append(phase[msk])        
        lol = data[['L1','L2','C1','P2'],sv,msk,'lli'] 
        lol[np.isnan(lol)] = 0
        lol = lol.astype(int)
        lol = np.logical_or.reduce((lol%2).T)
        lol = lol.astype(int) #store all hardware-determined loss of lock as a 1
        greg = np.isfinite(data['cslip',sv,msk,'data'].values) #mask of software determined cycle slips
        lol[greg] += 2 #add 2 to all times with cycle slips, HW=1, SW=2, both=3
        d['lol'].append(lol)
        d['TEC'].append(data['TEC',sv,:,'data'][msk])
        d['az2sat'].append(data['Az',sv,:,'data'][msk])
        d['el2sat'].append(data['El',sv,:,'data'][msk])
        d['recBias'].append(recbias*np.ones(len(data['TEC',sv,:,'data'][msk])))
        d['satnum'].append(sv*np.ones(len(data['TEC',sv,:,'data'][msk])))
        d['vTEC'].append(data['vTEC',sv,:,'data'][msk])
        d['nTEC'].append(data['nTEC',sv,:,'data'][msk])
        dataloc.append(data[['pplat','pplon','ppalt'],sv,:,'data'][msk])
        times.append(np.hstack((data.major_axis[msk][:,None],data.major_axis[msk][:,None]+1000000000)))
    
    d['raw'] = np.hstack(d['raw'])    
    d['lol'] = np.hstack(d['lol'])
    d['TEC'] = np.hstack(d['TEC'])
    d['az2sat'] = np.hstack(d['az2sat'])
    d['el2sat'] = np.hstack(d['el2sat'])
    d['recBias'] = np.hstack(d['recBias'])
    d['satnum'] = np.hstack(d['satnum'])
    d['vTEC'] = np.hstack(d['vTEC'])
    d['nTEC'] = np.hstack(d['nTEC'])
    coordnames = 'WGS84'
    dataloc = np.vstack(dataloc)
    sensorloc = np.nan*np.ones(3)
    times = np.vstack(times)    
    
    t0 = np.datetime64(datetime(1970,1,1),'ns')
    times = (times-t0).astype(float)/1.0E9
    
    
    return (d,coordnames,dataloc,sensorloc,times)

if __name__== '__main__':
    gd = GDfromRinex('/home/greg/Documents/greg/rinex/mah62800.15o',
                 '/home/greg/Documents/greg/brdc2800.15n',
                 '/home/greg/Documents/greg/jplg2800.15i',
                 '/home/greg/Documents/greg/P1C11510.DCB',
                 '/home/greg/Documents/greg/rinex/mah62800.h5',
                 False,130,[9,23])