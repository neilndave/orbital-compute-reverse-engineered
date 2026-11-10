"""Decode every QR code in a PNG with OpenCV (run with a python that has opencv). Prints JSON list of {data, x_center_px}.
Locates codes with detectAndDecodeMulti; any code it locates but fails to decode is re-decoded alone from a padded crop."""
import sys,json,cv2
img=cv2.imread(sys.argv[1]);det=cv2.QRCodeDetector()
ok,datas,pts,_=det.detectAndDecodeMulti(img)
out=[]
if ok:
  for d,p in zip(datas,pts):
    if not d:
      x0,y0=p.min(0);x1,y1=p.max(0);m=0.25*(x1-x0)
      crop=img[max(0,int(y0-m)):int(y1+m),max(0,int(x0-m)):int(x1+m)]
      d=det.detectAndDecode(crop)[0]
    out.append(dict(data=d,x_center_px=float(p[:,0].mean())))
print(json.dumps(out))
