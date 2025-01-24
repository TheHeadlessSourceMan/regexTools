import typing


def skipEmptyines(lines:typing.Union[str,typing.Iterable[str]]
    )->typing.Generator[str,None,None]:
    """
    Iterate over a series of lines, skipping empty ones
    """
    if isinstance(lines,str):
        lines=lines.replace('\r','').split('\n')
    for line in lines:
        if line:
            yield line

class StrWithFileLocation:
    """
    A string with the file location reference where it came from
    """
    def __init__(self,s:typing.Any,filename:str='',lineNo:int=0):
        self.lineNo:int=lineNo
        self.filename=filename
        if not isinstance(s,str):
            s=str(s)
        self.s=s

    def split(self,
        splitters=None,
        maxSplit=None
        )->typing.List["StrWithFileLocation"]:
        """
        split the string apart
        """
        ret=[]
        for x in self.s.split(splitters,maxSplit):
            ret.append(StrWithFileLocation(
                x,filename=self.filename,lineNo=self.lineNo))
        return ret
    def __eq__(self,other):
        return self.s==str(other)
    def __hash__(self):
        return hash(self.s)
    def __repr__(self):
        return self.s
strWithFileLocation=StrWithFileLocation # a few old things called it this.  Can probably remove pretty safely. # noqa: E501 # pylint: disable=line-too-long