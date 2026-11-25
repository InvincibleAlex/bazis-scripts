"""Shared article numbering for hardware inventory and assembly annotations."""
def article_key(fitting):
    return fitting.get('name','Feronerie').split('\r')[0].strip(),fitting.get('article','')

def assign_article_labels(hardware):
    numbers={}
    for fitting in hardware:
        if fitting.get('hidden'):continue
        key=article_key(fitting)
        if key not in numbers:numbers[key]=len(numbers)+1
        fitting.update(kind='hardware',label=numbers[key])
    return numbers
