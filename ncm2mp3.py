import binascii, struct, base64, json, os, eyed3, sys
from Crypto.Cipher import AES

count = [0, 0, 0] # [ncm found, ncm processed, mp3 already exist]

def ncmdump(f_ncm_path):
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s : s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    f_ncm = open(f_ncm_path,'rb')
    header = f_ncm.read(8)
    assert binascii.b2a_hex(header) == b'4354454e4644414d'
    f_ncm.seek(2, 1)
    key_length = f_ncm.read(4)
    key_length = struct.unpack('<I', bytes(key_length))[0]
    key_data = f_ncm.read(key_length)
    key_data_array = bytearray(key_data)
    for i in range (0,len(key_data_array)): key_data_array[i] ^= 0x64
    key_data = bytes(key_data_array)
    cryptor = AES.new(core_key, AES.MODE_ECB)
    key_data = unpad(cryptor.decrypt(key_data))[17:]
    key_length = len(key_data)
    key_data = bytearray(key_data)
    key_box = bytearray(range(256))
    c = 0
    last_byte = 0
    key_offset = 0
    for i in range(256):
        swap = key_box[i]
        c = (swap + last_byte + key_data[key_offset]) & 0xff
        key_offset += 1
        if key_offset >= key_length: key_offset = 0
        key_box[i] = key_box[c]
        key_box[c] = swap
        last_byte = c
    
    meta_length = f_ncm.read(4)
    meta_length = struct.unpack('<I', bytes(meta_length))[0]
    meta_data = f_ncm.read(meta_length)
    meta_data_array = bytearray(meta_data)
    for i in range(0,len(meta_data_array)): meta_data_array[i] ^= 0x63
    meta_data = bytes(meta_data_array)
    meta_data = base64.b64decode(meta_data[22:])
    cryptor = AES.new(meta_key, AES.MODE_ECB)
    meta_data = unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:]
    meta_data = json.loads(meta_data)
    #print(meta_data)

    crc32 = f_ncm.read(4)
    crc32 = struct.unpack('<I', bytes(crc32))[0]
    

    f_ncm.seek(5, 1)
    image_size = f_ncm.read(4)
    image_size = struct.unpack('<I', bytes(image_size))[0]
    image_data = f_ncm.read(image_size)

    f_music_name = os.path.splitext(os.path.basename(f_ncm_path))[0] + '.' + meta_data['format']

    f_music = open(os.path.join(os.path.dirname(f_ncm_path),f_music_name),'wb')
    
    chunk = bytearray()
    while True:
        chunk = bytearray(f_ncm.read(0x8000))
        chunk_length = len(chunk)
        if not chunk:
            break
        for i in range(1,chunk_length+1):
            j = i & 0xff;
            chunk[i-1] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
        f_music.write(chunk)

    f_music.close()
    f_ncm.close()

    if meta_data['format'] == 'mp3' or meta_data['format'] == 'MP3':
        audiofile = eyed3.load(os.path.join(os.path.dirname(f_ncm_path),f_music_name))
        audiofile.tag.artist = meta_data['artist'][0][0]
        audiofile.tag.album = meta_data['album']
        audiofile.tag.album_artist = meta_data['artist'][0][0]
        audiofile.tag.title = meta_data['musicName']
        audiofile.tag.images.set(3, image_data, "image/jpeg", description=u"Front Cover")
        audiofile.tag.save()

def ncm2mp3(path):

    global count
    
    if os.path.isfile(path):
        
        if os.path.splitext(path)[1] == '.ncm' or os.path.splitext(path)[1] == '.NCM':
            count[0] = count[0] + 1
            print("Processing file: %s" % (os.path.basename(path)))
            if (not os.path.exists(os.path.splitext(path)[0]+'.mp3')) and (not os.path.exists(os.path.splitext(path)[0]+'.MP3')):
                ncmdump(path)
                count[1] = count[1] + 1
            else:
                count[2] = count[2] + 1

    elif os.path.isdir(path):
        path_lst = os.listdir(path)
        for item in path_lst:
            ncm2mp3(os.path.join(path, item))

def main(path):
    global count
    if len(sys.argv) == 1:
        if path == '':
            ncm2mp3(sys.path[0])
        else:
            ncm2mp3(path)
    elif len(sys.argv) == 2:

        ncm2mp3(sys.argv[1])
    else:
        print("Too much arguments!")

    print("Found %d '.ncm' files; Processed %d '.ncm' files; Found %d corresponding '.mp3' files already exist." %(count[0], count[1], count[2]))


if __name__ == '__main__':
    path = '' #Put file or folder path here.
    main(path)
  
