"""
Code for implementing a python controller for Texas Instruments DLPLCR6500.
This code is based on the following project: https://github.com/csi-dcsc/Pycrafter6500 , by Paolo Pozzi.

****************************************
This version of the device class uses as library the hidapi python wrapper.

Consider to use the device file using pywinusb.hid library instead of this one
if someday the latter does not work, since it's not maintained (I think...),
while the pywinusb is (I think...). 

For the detailed comprehension of the code, please refer to the manual (search DLP900 programmer's guide).
****************************************

-Michele Castriotta (@mikics on github), PhD at Politecnico di Milano.
-Andrea Bassi;
-Gianmaria Calisesi;

20/02/19
"""

import hid
import time
import numpy
import os
import pickle

class DmdDeviceHID:
    
    def __init__(self):
        
        hid.enumerate()
        self.device = hid.Device(vid=0x0451, pid=0xc900)
        time.sleep(0.5)
        #self.device.open(0x0451, 0xc900) #open the communication
        #self.device.open(0x0145, 0x022E) #open the communication
        # print(self.device.get_manufacturer_string())
        # print(self.device.get_product_string())
        # print(self.device.get_serial_number_string())
        self.ans = []

    def command(self,mode,sequencebyte,com1,com2,data=None):
        buffer = []

        flagstring=''
        if mode=='r':
            flagstring+='1'
        else:
            flagstring+='0'        
        flagstring+='1000000' #the one indicates we want an answer by the device.
        buffer.append(0x0)
        buffer.append(bitstobytes(flagstring)[0])
        buffer.append(sequencebyte)
        temp=bitstobytes(convlen(len(data)+2,16))
        buffer.append(temp[0])
        buffer.append(temp[1])
        buffer.append(com2) 
        buffer.append(com1)

        if len(buffer)+len(data)<=65: #65 = max number of sent bytes 
        
            for i in data:
                buffer.append(i)

            for i in range(65-len(buffer)):
                buffer.append(0x00)


            self.device.write(buffer)

        else:
            for i in range(65-len(buffer)):
                buffer.append(data[i])

            self.device.write(buffer)

            buffer = [0x00]

            j=0
            while j<len(data)-58:
                buffer.append(data[j+58])
                j=j+1
                if j%64==0: #we need 64 instead of 65
                    self.device.write(buffer)

                    buffer = [0x00]

            if j%64!=0:

                while j%64!=0:
                    buffer.append(0x00)
                    j=j+1
                    
                self.device.write(buffer)               
                

    def checkforerrors(self):
        """
        This part needs to be checked
        """
        self.ans = self.device.read(1)
        self.flag = convlen(self.ans[0], 8)
        #print(self.flag)
#         length = convlen(self.ans[3], 8)
#         length = length+convlen(self.ans[4], 8)
#         print(length)
#         num = int(length, 2)
#         print(num)
#         self.device.read(num)
        if self.flag[2]=="1":
            print("An error occurred! --> ", self.ans)
            self.command('r',0x22,0x01,0x00,[])
            self.error = self.device.read(1)

            self.command('r',0x22,0x01,0x01,[])
            self.response = self.device.read(128)
        #print(self.response)




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

#         trigg1 = convlen(0,1)
#         trigg1 = bitstobytes(trigg1)
#         trigg2 = convlen(0, 16)
#         trigg2 = bitstobytes(trigg2)
#         trigg3 = convlen(20, 16)
#         trigg3 = bitstobytes(trigg3)
#         triggering = []
#         for i in trigg1:
#             triggering.append(i)
#         for i in trigg2:
#             triggering.append(i)
#         for i in trigg3:
#             triggering.append(i)
#         self.command('w', 0x00, 0x1a, 0x1e, triggering)
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

            self.command('w',0x11,0x1a,0x2b,payload) #0x11 is for a response, IDK if we need it

            #self.command('w',0x11,0x1a,0x2d,payload) #read page 57 of programmer guide
            self.checkforerrors()
        print("Time for loading: ", time.clock()-t)

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
        
        self.configurelut(num,rep)
        
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
        

        for i in range(int((num-1)//24)+1): #for i in range(len(encodedimages)) should work?
            self.setbmp(int((num-1)//24)-i,sizes[int((num-1)//24)-i])
            print ('uploading...')
            self.bmpload(encodedimages[int((num-1)//24)-i],sizes[int((num-1)//24)-i])
            
        print ("Total time: ", time.clock()-t)

    def def_sequence_by_file(self,files,exp,ti,dt,to,rep):
        """
        Function that define the sequence of images on the pattern by fetching
        the encoding and all other necessary data from an .encd file.
        """
        self.stopsequence()
        
        files = pickle.load(open(files, "rb"))
        
        number_images = files[0]
        encoded_images = files[1]
        images_sizes = files[2]
        
        exp = exp*number_images
        ti = ti*number_images
        dt = dt*number_images
        to = to*number_images
        
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
        
        return number_images
            
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

if __name__ == "__main__":
    
    hiddev = DmdDeviceHID()

    import PIL.Image

    try:
        #hiddev.reset()
        images=[]
         
        directory_in_str = "X:\\Gianmaria\\DMD\\Patterns\\DMD_patterns\\bin_sinusoidal_pattern\\"
        directory = os.fsencode(directory_in_str)
        i = 0
        for file in sorted(os.listdir(directory)):
            filename = os.fsdecode(file)
            if filename.endswith("320.png"):
                """
                Here is necessary to speciofy the array as boolean, since, otherwise, python
                sees an 8 bit image, adn, when we merge images, there are overflow issues, besides
                of issues in adding patterns. With boolean, I think, Python automatically transforms
                the image in a "boolean" image.
                """
                arr = numpy.asarray(PIL.Image.open(directory_in_str+filename), dtype = numpy.bool)
                images.append(arr)
                i += 1
            if i > 1:
                break
     
        hiddev.changemode(3)
        
        exposure=[1000000]*len(images)
        dark_time=[0]*len(images)
        trigger_in=[False]*len(images)
        trigger_out=[True]*len(images)
        
        hiddev.defsequence(images,exposure,trigger_in,dark_time,trigger_out, 60)
        
        hiddev.startsequence()
        work = "y"
        while work != "n":
            work = input()
    finally:
        hiddev.stopsequence()
        print("stopped")