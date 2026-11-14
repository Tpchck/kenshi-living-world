import sys,collections
sys.path.insert(0,r"C:\KenshiModMap\tools")
import kmod
W=r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
for p in [W+r"\3787280895\RidingPlugin.mod",W+r"\3791607178\VanillaRace4CharactersEmotions.mod",W+r"\3791017374\CharactersEmotions.mod"]:
    m=kmod.read(p); print("==",p); h=m.header; print(vars(h) if hasattr(h,'__dict__') else h)
    c=collections.Counter()
    for it in m.items:
        c[(it.type_name,it.change)]+=1
        print(" ",it.type_name,it.change,it.sid if hasattr(it,'sid') else '',getattr(it,'name',''))
    print(c)
