import qrcode
from PIL import Image


data = {
    "example":[
    
        {
            "word": "byte",
            "meaning": "A group of eight bits, often likened to a crumb of digital sustenance.",
            "points": 20
        },
        {
            "word": "scroll",
            "meaning": "To peruse the written word on a digital parchment, often with a wheel or gesture.",
            "points": 30
        },
        {
            "word": "download",
            "meaning": "To fetch information from the ethereal digital realm and bring it hither to thy device.",
            "points": 40
        },
    ]
    
}

img= qrcode.make(data=data,box_size=4,
        border=5)

print(img.save("book_qrcodes/hello-kitty-26-2023-10-19-09-38-38.png"))
