import re
from dataclasses import asdict, dataclass, field

COLORS=["dark green","dark blue","black","white","red","blue","green","yellow","orange","pink","purple","brown","gray"]
OBJECT_ALIASES={"dog":"dog","backpack":"backpack","rucksack":"backpack","handbag":"handbag","purse":"handbag","bag":"bag","phone":"phone","cellphone":"phone","mobile":"phone","bicycle":"bicycle","bike":"bicycle","car":"car","bottle":"bottle"}
RELATION_WORDS={"carrying":"carrying","carry":"carrying","holding":"holding","hold":"holding","with":"with","wearing":"wearing","next to":"next_to","near":"next_to","riding":"riding"}
@dataclass
class ParsedQuery:
    subject_class: str = "person"
    gender: str | None = None
    upper_type: str | None = None
    upper_color: str | None = None
    lower_type: str | None = None
    lower_color: str | None = None
    accessories: list[str] = field(default_factory=list)
    objects_held: list[str] = field(default_factory=list)
    object_class: str | None = None
    relationship: str | None = None
    action: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    def dict(self): return asdict(self)

def parse_query(text: str) -> ParsedQuery:
    q=" ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    p=ParsedQuery()
    if re.search(r"\b(man|men|boy|boys|male)\b", q): p.gender="male"
    elif re.search(r"\b(woman|women|girl|girls|female)\b", q): p.gender="female"
    clothing={"hoodie":"hoodie","jacket":"jacket","coat":"coat","sweater":"sweater","shirt":"shirt","t shirt":"tshirt","top":"shirt","dress":"dress"}
    for term,value in clothing.items():
        if re.search(rf"\b{re.escape(term)}\b",q): p.upper_type=value; break
    for color in COLORS:
        if color in q:
            if any(word in q for word in ("lower clothing", "lower clothes", "pants", "trousers", "shorts", "skirt")):
                p.lower_color=color.replace(" ","_")
            else: p.upper_color=color.replace(" ","_")
            break
    for term,value in OBJECT_ALIASES.items():
        if re.search(rf"\b{re.escape(term)}\b",q): p.object_class=value; break
    for phrase,value in RELATION_WORDS.items():
        if phrase in q: p.relationship=value; break
    if p.object_class in {"backpack","handbag"}: p.accessories.append(p.object_class)
    if p.object_class in {"phone","bottle"} and p.relationship in {"holding","carrying"}: p.objects_held.append(p.object_class)
    actions={"walking":"walk","walked":"walk","walk":"walk","running":"run","ran":"run","run":"run","riding":"riding","ride":"riding","waving":"wave","wave":"wave"}
    for term,action in actions.items():
        if re.search(rf"\b{term}\b",q): p.action=action; break
    around=re.search(r"around\s+(\d+)\s+minutes?",q)
    if around: p.start_seconds=int(around.group(1))*60-30; p.end_seconds=int(around.group(1))*60+30
    if p.object_class and not (p.gender or p.upper_type or p.upper_color or p.relationship or p.action or re.search(r"\b(person|people|man|woman|boy|girl)\b",q)): p.subject_class="object"
    return p
