"""
Code for implementing a python controller for Texas Instruments DLPLCR6500.
This code is based on the following project (https://github.com/csi-dcsc/Pycrafter6500 , by Paolo Pozzi).

****************************************
This version uses the libusb library. I would not recommend it since I had some problems with 
the connection while sending data to the device. Try instead the other version of the device class,
(DMDDeviceHID) which uses the hidapi python wrapper.
****************************************

Michele Castriotta (@mikics on github), MSc at Politecnico di Milano.
Andrea Bassi

12/12/18
"""

import usb.core
import time
import numpy
import PIL.Image
import pickle
import os
import usb.backend.libusb1 as libusb1

class DmdDevice:
    
    def __init__(self, idVendor=0x0451, idProduct=0xc900):
        
        self.dev=usb.core.find(idVendor=idVendor ,idProduct=idProduct, backend=libusb1.get_backend())
        print(self.dev)
        self.dev.set_configuration()
        self.ans=[]

## standard usb command function

    def command(self,mode,sequencebyte,com1,com2,data=None):
        buffer = []

        flagstring=''
        if mode=='r':
            flagstring+='1'
        else:
            flagstring+='0'        
        flagstring+='1000000'
        buffer.append(bitstobytes(flagstring)[0])
        buffer.append(sequencebyte)
        temp=bitstobytes(convlen(len(data)+2,16))
        buffer.append(temp[0])
        buffer.append(temp[1])
        buffer.append(com2)
        buffer.append(com1)

        if len(buffer)+len(data)<65:
        
            for i in data:
                buffer.append(i)

            for i in range(64-len(buffer)):
                buffer.append(0x00)


            self.dev.write(1, buffer, timeout = 1000)

        else:
            for i in range(64-len(buffer)):
                buffer.append(data[i])

            self.dev.write(1, buffer, timeout = 1000)

            buffer = []

            j=0
            while j<len(data)-58:
                buffer.append(data[j+58])
                j=j+1
                if j%64==0:
                    self.dev.write(1, buffer, timeout = 1000)

                    buffer = []

            if j%64!=0:

                while j%64!=0:
                    buffer.append(0x00)
                    j=j+1
                    
                self.dev.write(1, buffer, timeout = 1000)                
                
        self.ans=self.dev.read(0x81,64, timeout = 1000)

## functions for checking error reports in the dlp answer

    def checkforerrors(self):
        self.command('r',0x22,0x01,0x00,[])
        if self.ans[6]!=0:
            print (self.ans[6])    

## function printing all of the dlp answer

    def readreply(self):
        for i in self.ans:
            print (hex(i))

## functions for idle mode activation

    def idle_on(self):
        self.command('w',0x00,0x02,0x01,[int('00000001',2)])
        self.checkforerrors()

    def idle_off(self):
        self.command('w',0x00,0x02,0x01,[int('00000000',2)])
        self.checkforerrors()

## functions for power management

    def standby(self):
        self.command('w',0x00,0x02,0x00,[int('00000001',2)])
        self.checkforerrors()

    def wakeup(self):
        self.command('w',0x00,0x02,0x00,[int('00000000',2)])
        self.checkforerrors()

    def reset(self):
        self.command('w',0x00,0x02,0x00,[int('00000010',2)])
        self.checkforerrors()

## test write and read operations, as reported in the dlpc900 programmer's guide

    def testread(self):
        self.command('r',0xff,0x11,0x00,[])
        self.readreply()

    def testwrite(self):
        self.command('w',0x22,0x11,0x00,[0xff,0x01,0xff,0x01,0xff,0x01])
        self.checkforerrors()

## some self explaining functions

    def changemode(self,mode):
        self.command('w',0x00,0x1a,0x1b,[mode])
        self.checkforerrors()

    def startsequence(self):
        self.command('w',0x00,0x1a,0x24,[2])
        self.checkforerrors()

    def pausesequence(self):
        self.command('w',0x00,0x1a,0x24,[1])
        self.checkforerrors()

    def stopsequence(self):
        self.command('w',0x00,0x1a,0x24,[0])
        self.checkforerrors()


    def configurelut(self,imgnum,repeatnum):
        img=convlen(imgnum,11)
        repeat=convlen(repeatnum,32)

        string=repeat+'00000'+img

        im_bytes=bitstobytes(string)

        self.command('w',0x00,0x1a,0x31,im_bytes)
        self.checkforerrors()

    def definepattern(self,index,exposure,bitdepth,color,triggerin,darktime, triggerout,patind,bitpos):
        payload=[]
        index=convlen(index,16)
        index=bitstobytes(index)
        for i in index:
            payload.append(i)

        exposure=convlen(exposure,24) #24 or 32?
        exposure=bitstobytes(exposure)
        for i in exposure:
            payload.append(i)
            
        optionsbyte=''
        #optionsbyte+='0'*8 #I put this line. I dont know if it's right. see the manual
        optionsbyte+='1'
        bitdepth=convlen(bitdepth-1,3)
        optionsbyte=bitdepth+optionsbyte
        optionsbyte=color+optionsbyte
        if triggerin:
            optionsbyte='1'+optionsbyte
        else:
            optionsbyte='0'+optionsbyte

        payload.append(bitstobytes(optionsbyte)[0])

        darktime=convlen(darktime,24)
        darktime=bitstobytes(darktime)
        for i in darktime:
            payload.append(i)

        triggerout=convlen(not triggerout,8)
        triggerout=bitstobytes(triggerout)
        for i in triggerout:
            payload.append(i)

        patind=convlen(patind,11)
        bitpos=convlen(bitpos,5)
        lastbits=bitpos+patind
        lastbits=bitstobytes(lastbits)
        for i in lastbits:
            payload.append(i)

        trigg1 = convlen(0,1)
        trigg1 = bitstobytes(trigg1)
        trigg2 = convlen(0, 16)
        trigg2 = bitstobytes(trigg2)
        trigg3 = convlen(20, 16)
        trigg3 = bitstobytes(trigg3)
        triggering = []
        for i in trigg1:
            triggering.append(i)
        for i in trigg2:
            triggering.append(i)
        for i in trigg3:
            triggering.append(i)
        self.command('w', 0x00, 0x1a, 0x1e, triggering)
        self.command('w',0x00,0x1a,0x34,payload)
        self.checkforerrors()
        
    

    def setbmp(self,index,size):
        payload=[]

        index=convlen(index,5)
        index='0'*11+index
        index=bitstobytes(index)
        for i in index:
            payload.append(i) 


        total=convlen(size,32)
        total=bitstobytes(total)
        for i in total:
            payload.append(i)         
        
        self.command('w',0x00,0x1a,0x2a,payload)
        #self.command('w',0x00,0x1a,0x2c,payload) #read page 57 of programmer guide
        self.checkforerrors()

## bmp loading function, divided in 56 bytes packages
## max  hid package size=64, flag bytes=4, usb command bytes=2
## size of package description bytes=2. 64-4-2-2=56

    def bmpload(self,image,size):

        t=time.clock()

        packnum=int(size//504)+1

        counter=0

        for i in range(packnum):
            
            if i %100==0:
                print (i,packnum)
                
            payload=[]
            
            if i<packnum-1:
                leng=convlen(504,16)
                bits=504
            else:
                leng=convlen(size%504,16)
                bits=size%504
                
            leng=bitstobytes(leng)
            
            for j in range(2):
                payload.append(leng[j])
                
            for j in range(bits):
                payload.append(image[counter])
                counter+=1
            
            self.command('w',0x11,0x1a,0x2b,payload)
            #self.command('w',0x11,0x1a,0x2d,payload) #read page 57 of programmer guide
            self.checkforerrors()
            
        print("Time for loading: ", time.clock()-t)

#     def save_encoded_sequence(self, images):
#         
#         arr=[]
# 
#         for i in images:
#             arr.append(i)
# 
# ##        arr.append(numpy.ones((1080,1920),dtype='uint8'))
#         num=len(arr)
# 
#         encodedimages=[]
#         sizes=[]
#         files = []
#         for i in range(int((num-1)//24)+1):
#             print ('merging...')
#             if i<(int((num-1)//24)):
#                 imagedata=mergeimages(arr[i*24:(i+1)*24])
#             else:
#                 imagedata=mergeimages(arr[i*24:])
#             
# 
#             print('encoding...')
#             
#             imagedata,size=new_encode(imagedata)
#             
# 
#             encodedimages.append(imagedata)
#             sizes.append(size)
#             
#         date = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
#         files = [num, encodedimages, sizes]
#         
#         pickle.dump(files, open("E:\\LabPrograms\\Python\\DMD_ScopeFoundry\\pattern\\encodedimage" + date + '.encd', 'wb'), pickle.HIGHEST_PROTOCOL)
# #         pickle.dump(sizes, open("E:\\LabPrograms\\Python\\DMD_ScopeFoundry\\pattern\\sizes" + date + '.encd', 'wb'), pickle.HIGHEST_PROTOCOL)
# #         pickle.dump(num, open("E:\\LabPrograms\\Python\\DMD_ScopeFoundry\\pattern\\num" + date + '.encd', 'wb'), pickle.HIGHEST_PROTOCOL)
        
    def def_sequence_by_file(self, files,exp,ti,dt,to,rep):
        """
        Function that define the sequence of images on the pattern by fetching
        the encoding and all other necessary data from an .encd file.
        """
        self.stopsequence()
        
        files = pickle.load(open(files, "rb"))
        
        number_images = files[0]
        encoded_images = files[1]
        images_sizes = files[2]
        
        exp = [exp]*number_images
        ti = [ti]*number_images
        dt = [dt]*number_images
        to = [to]*number_images
        
        for i in range(int((number_images-1)//24)+1):
            
            if i<(int((number_images-1)//24)):
                for j in range(i*24,(i+1)*24):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)
            else:
                for j in range(i*24,number_images):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)
                    
        self.configurelut(number_images,rep)

        for i in range(int((number_images-1)//24)+1): 
            self.setbmp(int((number_images-1)//24)-i,images_sizes[int((number_images-1)//24)-i])
            print ('uploading...')
            self.bmpload(encoded_images[int((number_images-1)//24)-i],images_sizes[int((number_images-1)//24)-i])
            
    def defsequence(self,images,exp,ti,dt,to,rep):

        self.stopsequence()

        arr=[]

        for i in images:
            arr.append(i)

##        arr.append(numpy.ones((1080,1920),dtype='uint8'))
        num=len(arr)

        encodedimages=[]
        sizes=[]
        t=time.clock()

        for i in range(int((num-1)//24)+1):
            print ('merging...')
            if i<(int((num-1)//24)):
                imagedata=mergeimages(arr[i*24:(i+1)*24])
            else:
                imagedata=mergeimages(arr[i*24:])
            

            print('encoding...')
            
            imagedata,size=new_encode(imagedata)
            

            encodedimages.append(imagedata)
            sizes.append(size)

            if i<(int((num-1)//24)):
                for j in range(i*24,(i+1)*24):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)
            else:
                for j in range(i*24,num):
                    self.definepattern(j,exp[j],1,'111',ti[j],dt[j],to[j],i,j-i*24)
        
        print ("Time for merging and encoding: ", time.clock()-t)
        self.configurelut(num,rep)

        for i in range(int((num-1)//24)+1): #for i in range(len(encodedimages)) should work?
            self.setbmp(int((num-1)//24)-i,sizes[int((num-1)//24)-i])
            print ('uploading...')
            self.bmpload(encodedimages[int((num-1)//24)-i],sizes[int((num-1)//24)-i])
            
        print ("Total time: ", time.clock()-t)

def save_encoded_sequence(images, folder, name):
    
    """
    Function that save an encoded sequence of image into a file.
    """
        
    arr=[]

    for i in images:
        arr.append(i)

    num=len(arr)

    encodedimages=[]
    sizes=[]
    
    for i in range(int((num-1)//24)+1):
        print ('merging...')
        if i<(int((num-1)//24)):
            imagedata=mergeimages(arr[i*24:(i+1)*24])
        else:
            imagedata=mergeimages(arr[i*24:])
        

        print('encoding...')
        
        imagedata,size=new_encode(imagedata)
        

        encodedimages.append(imagedata)
        sizes.append(size)
        
    files = [num, encodedimages, sizes]
    if not os.path.isdir(folder):
        os.makedirs(folder)
    pickle.dump(files, open(folder + name + '.encd', 'wb'), pickle.HIGHEST_PROTOCOL)

def convlen(a,l):
    """
    This function converts a number "a" into a bit string of
    length "l".
    """
    b=bin(a)[2:]
    padding=l-len(b)
    b='0'*padding+b

    return b

def bitstobytes(a):
    """
    This function converts a bit string into a given nuymber of bytes
    """
    bytelist=[]
    
    if len(a)%8!=0: #if length is not a multiple of 8, make it a multiple.
        padding=8-len(a)%8
        a='0'*padding+a
        
    for i in range(int(len(a)//8)): #put the bit in an array of byte
        bytelist.append(int(a[8*i:8*(i+1)],2))

    bytelist.reverse() #reverse the list

    return bytelist

def mergeimages(images):
    """
    function that encodes a 8 bit numpy array matrix as a enhanced run length encoded string of bits
    """
    mergedimage=numpy.zeros((1080,1920,3),dtype='uint8') #put this as numpy.uint8?

    for i in range(len(images)):
        
        if i<8:
            mergedimage[:,:,2]=mergedimage[:,:,2]+images[i]*(2**i) #with the multiplication, the 8 bit pixel contains the info abopu all the 8 images (if we are in binary...)

        if i>7 and i<16:
            mergedimage[:,:,1]=mergedimage[:,:,1]+images[i]*(2**(i-8))

        if i>15 and i<24: #maybe 24 because in RGB you have 8*3
            mergedimage[:,:,0]=mergedimage[:,:,0]+images[i]*(2**(i-16))
            
    return mergedimage

def new_encode(image):
    """
    I have rewritten the encoding function to make it clearer and straightforward.
    Besides, I have deleted the condition for which the function remains trapped
    in an infinite loop for some hadamard pattern. Everything seems to work fine.
    """


## header creation
    bytecount=48    
    bitstring=[]

    bitstring.append(0x53)
    bitstring.append(0x70)
    bitstring.append(0x6c)
    bitstring.append(0x64)
    
    width=convlen(1920,16)
    width=bitstobytes(width)
    for i in width:
        bitstring.append(i)

    height=convlen(1080,16)
    height=bitstobytes(height)
    for i in height:
        bitstring.append(i)


    total=convlen(0,32)
    total=bitstobytes(total)
    for i in total:
        bitstring.append(i)        

    for i in range(8):
        bitstring.append(0xff)

    for i in range(4):    ## black curtain
        bitstring.append(0x00)

    bitstring.append(0x00)

    bitstring.append(0x02) ## enhanced rle

    bitstring.append(0x01)

    for i in range(21):
        bitstring.append(0x00)

    n=0
    i=0
    j=0

    while i <1080:

        while j <1920:

            if i>0:
                if numpy.all(image[i,j,:]==image[i-1,j,:]):
                    while j<1920 and numpy.all(image[i,j,:]==image[i-1,j,:]):
                        n=n+1
                        j=j+1
                        
    
                    bitstring.append(0x00)
                    bitstring.append(0x01)
                    bytecount+=2
                    
                    if n>=128:
                        byte1=(n & 0x7f)|0x80
                        byte2=(n >> 7)
                        bitstring.append(byte1)
                        bitstring.append(byte2)
                        bytecount+=2
                        
                    else:
                        bitstring.append(n)
                        bytecount+=1
                    n=0

            
                else:
                    if j < 1919: #1919 since I compare j and j+1 pixel
                        if numpy.all(image[i,j,:]==image[i,j+1,:]):
                            n=n+1
                    
                            while j<1919 and numpy.all(image[i,j,:]==image[i,j+1,:]):
                                n=n+1
                                j=j+1
                            if n>=128:
                                byte1=(n & 0x7f)|0x80
                                byte2=(n >> 7)
                                bitstring.append(byte1)
                                bitstring.append(byte2)
                                bytecount+=2
                                
                            else:
                                bitstring.append(n)
                                bytecount+=1
        
                            bitstring.append(image[i,j-1,0])
                            bitstring.append(image[i,j-1,1])
                            bitstring.append(image[i,j-1,2])
                            bytecount+=3
                            
                            j=j+1
                            n=0
                        elif j > 1917 or numpy.all(image[i,j+1,:]==image[i,j+2,:]) or numpy.all(image[i,j+1,:]==image[i-1,j+1,:]):
                            bitstring.append(0x01)
                            bytecount+=1
                            bitstring.append(image[i,j,0])
                            bitstring.append(image[i,j,1])
                            bitstring.append(image[i,j,2])
                            bytecount+=3
                            
                            j=j+1
                            n=0
                        else:
                            bitstring.append(0x00)
                            bytecount+=1
    
                            toappend=[]
    
                            while j<1919 and numpy.any(image[i,j,:]!=image[i,j+1,:]):

                                """
                                I've moved the j<1919 condition as first condition since sometimes it
                                tries to read image array at wrong index.
                                """
                                n=n+1
                                toappend.append(image[i,j,0])
                                toappend.append(image[i,j,1])
                                toappend.append(image[i,j,2])
                                j=j+1
                                
                            if n>=128:
                                byte1=(n & 0x7f)|0x80
                                byte2=(n >> 7)
                                bitstring.append(byte1)
                                bitstring.append(byte2)
                                bytecount+=2
    
                            else:
                                bitstring.append(n)
                                bytecount+=1
    
    
                            for k in toappend:
                                bitstring.append(k)
                                bytecount+=1
                            #j=j+1
                            n=0                           
                    elif j == 1919:
                        
                        bitstring.append(0x01)
                        bytecount+=1
                        bitstring.append(image[i,j,0])
                        bitstring.append(image[i,j,1])
                        bitstring.append(image[i,j,2])
                        bytecount+=3
                        
                        j=j+1
                        n=0
            else:
                
                if j < 1919: #1919 since I compare j and j+1 pixel
                
                    if numpy.all(image[i,j,:]==image[i,j+1,:]):
                        n=n+1
                
                        while j<1919 and numpy.all(image[i,j,:]==image[i,j+1,:]):
                            n=n+1
                            j=j+1
                        if n>=128:
                            byte1=(n & 0x7f)|0x80
                            byte2=(n >> 7)
                            bitstring.append(byte1)
                            bitstring.append(byte2)
                            bytecount+=2
                            
                        else:
                            bitstring.append(n)
                            bytecount+=1
    
                        bitstring.append(image[i,j-1,0])
                        bitstring.append(image[i,j-1,1])
                        bitstring.append(image[i,j-1,2])
                        bytecount+=3
                        
                        j=j+1
                        n=0
                    elif j > 1917 or numpy.all(image[i,j+1,:]==image[i,j+2,:]) or numpy.all(image[i,j+1,:]==image[i-1,j+1,:]):
                        bitstring.append(0x01)
                        bytecount+=1
                        bitstring.append(image[i,j,0])
                        bitstring.append(image[i,j,1])
                        bitstring.append(image[i,j,2])
                        bytecount+=3
                        
                        j=j+1
                        n=0
                    else:
                        bitstring.append(0x00)
                        bytecount+=1

                        toappend=[]

                        while j<1919 and numpy.any(image[i,j,:]!=image[i,j+1,:]):

                            """
                            I've moved the j<1919 condition as first condition since sometimes it
                            tries to read image array at wrong index.
                            """
                            n=n+1
                            toappend.append(image[i,j,0])
                            toappend.append(image[i,j,1])
                            toappend.append(image[i,j,2])
                            j=j+1
                            
                        if n>=128:
                            byte1=(n & 0x7f)|0x80
                            byte2=(n >> 7)
                            bitstring.append(byte1)
                            bitstring.append(byte2)
                            bytecount+=2

                        else:
                            bitstring.append(n)
                            bytecount+=1


                        for k in toappend:
                            bitstring.append(k)
                            bytecount+=1
                        #j=j+1
                        n=0                           
                elif j == 1919:
                    
                    bitstring.append(0x01)
                    bytecount+=1
                    bitstring.append(image[i,j,0])
                    bitstring.append(image[i,j,1])
                    bitstring.append(image[i,j,2])
                    bytecount+=3
                    
                    j=j+1
                    n=0
    
        j=0
        i=i+1
        bitstring.append(0x00)
        bitstring.append(0x00)
        bytecount+=2
    bitstring.append(0x00)
    bitstring.append(0x01)
    bitstring.append(0x00)
    bytecount+=3


    while (bytecount)%4!=0:
        bitstring.append(0x00)
        bytecount+=1        

    size=bytecount

    print (size)

    total=convlen(size,32)
    total=bitstobytes(total)
    for i in range(len(total)):
        bitstring[i+8]=total[i]    
    
    
    return bitstring, bytecount

            
def encode(image):
    """
    Encodes the image using the RLE compression (see manual of TI)
    """
## header creation
    bytecount=48    
    bitstring=[]

    bitstring.append(0x53)
    bitstring.append(0x70)
    bitstring.append(0x6c)
    bitstring.append(0x64)
    
    width=convlen(1920,16)
    width=bitstobytes(width)
    for i in width:
        bitstring.append(i)

    height=convlen(1080,16)
    height=bitstobytes(height)
    for i in height:
        bitstring.append(i)


    total=convlen(0,32)
    total=bitstobytes(total)
    for i in total:
        bitstring.append(i)        

    for i in range(8):
        bitstring.append(0xff)

    for i in range(4):    ## black curtain
        bitstring.append(0x00)

    bitstring.append(0x00)

    bitstring.append(0x02) ## enhanced rle

    bitstring.append(0x01)

    for i in range(21):
        bitstring.append(0x00)

    n=0
    i=0
    j=0

    while i <1080:

        while j <1920:
            
            if i>0 and numpy.all(image[i,j,:]==image[i-1,j,:]):
                
                while j<1920 and numpy.all(image[i,j,:]==image[i-1,j,:]):
                    n=n+1
                    j=j+1
                    

                bitstring.append(0x00)
                bitstring.append(0x01)
                bytecount+=2
                
                if n>=128:
                    byte1=(n & 0x7f)|0x80
                    byte2=(n >> 7)
                    bitstring.append(byte1)
                    bitstring.append(byte2)
                    bytecount+=2
                    
                else:
                    bitstring.append(n)
                    bytecount+=1
                n=0

            
            else:
                
                if j<1919 and numpy.all(image[i,j,:]==image[i,j+1,:]):
                    n=n+1
                    
                    while j<1919 and numpy.all(image[i,j,:]==image[i,j+1,:]):
                        n=n+1
                        j=j+1
                    if n>=128:
                        byte1=(n & 0x7f)|0x80
                        byte2=(n >> 7)
                        bitstring.append(byte1)
                        bitstring.append(byte2)
                        bytecount+=2
                        
                    else:
                        bitstring.append(n)
                        bytecount+=1

                    bitstring.append(image[i,j-1,0])
                    bitstring.append(image[i,j-1,1])
                    bitstring.append(image[i,j-1,2])
                    bytecount+=3
                    
                    j=j+1
                    n=0

                else:
                    
                    if j>1917 or numpy.all(image[i,j+1,:]==image[i,j+2,:]) or numpy.all(image[i,j+1,:]==image[i-1,j+1,:]):
                        
                        bitstring.append(0x01)
                        bytecount+=1
                        bitstring.append(image[i,j,0])
                        bitstring.append(image[i,j,1])
                        bitstring.append(image[i,j,2])
                        bytecount+=3
                        
                        j=j+1
                        n=0


                    else:
                        
                        bitstring.append(0x00)
                        bytecount+=1

                        toappend=[]

                        while j<1919 and numpy.any(image[i,j,:]!=image[i,j+1,:]) and numpy.any(image[i,j,:]!=image[i-1,j,:]):

                            """
                            I've moved the j<1919 condition as first condition since sometimes it
                            tries to read image array at wrong index.
                            """
                            """
                            The last above condition (numpy.any(image[i,j,:]!=image[i-1,j,:])) gave me
                            some problems because, for certain images, the condition is not satisfied
                            and we are trapped in an infinite loop since the j is not updated. In 
                            particular with the negated hadamard images with spatial frequency of 1 pixel.
                            
                            Anyway, this loop is the loop for i == 0, and there are for sure some 
                            problems for that condition since i-1 refer to the last row for i =0.
                            Then, it is not senseful for me. In the new_encode function I have
                            eliminated this condition, and everything seems to work fine.
                            """
                            n=n+1
                            toappend.append(image[i,j,0])
                            toappend.append(image[i,j,1])
                            toappend.append(image[i,j,2])
                            j=j+1
                            
                        if n>=128:
                            byte1=(n & 0x7f)|0x80
                            byte2=(n >> 7)
                            bitstring.append(byte1)
                            bitstring.append(byte2)
                            bytecount+=2

                        else:
                            bitstring.append(n)
                            bytecount+=1

                        for k in toappend:
                            bitstring.append(k)
                            bytecount+=1
                        #j=j+1
                        n=0
        j=0
        i=i+1
        bitstring.append(0x00)
        bitstring.append(0x00)
        bytecount+=2
    bitstring.append(0x00)
    bitstring.append(0x01)
    bitstring.append(0x00)
    bytecount+=3

    while (bytecount)%4!=0:
        bitstring.append(0x00)
        bytecount+=1        

    size=bytecount

    print (size)

    total=convlen(size,32)
    total=bitstobytes(total)
    for i in range(len(total)):
        bitstring[i+8]=total[i]    

    return bitstring, bytecount

if __name__ == '__main__':
    
    images=[]

    images.append(numpy.asarray(PIL.Image.open("cat.tif"), dtype = numpy.uint8))
    
    dlp=DmdDevice()
    
    dlp.stopsequence()
    
    dlp.changemode(3)
    
    exposure=[1000000]*30
    dark_time=[0]*30
    trigger_in=[False]*30
    trigger_out=[1]*30
    
    dlp.defsequence(images,exposure,trigger_in,dark_time,trigger_out,0)
    
    dlp.startsequence()
        
    while True:
        pass
    
    dlp.stopsequence()
    
