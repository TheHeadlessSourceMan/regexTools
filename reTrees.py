"""
Tool to split documents into trees using regexes.

Basically a poor-mans' parser.
"""
import typing
from collections.abc import Iterable,Mapping
import json
import regex


def refix(
    regexp:typing.Union[typing.Pattern,str],
    flags:typing.Union[int,str,typing.Iterable[str]]=0
    )->typing.Pattern:
    """
    Fix up a regexp to always be a compiled regular expression.

    If it is one, leave it alone.  If not, compile it.

    Note: In my experience re.MULTILINE doesn't work like i'd expect
    so this allows it to do that as well.

    :regexp: a string or regular expression
    :flags: an int, a flag name as a string, or a series of string flag names.

    returns a regex
    """
    unflags={
        'DOTALL':regex.DOTALL,
        'MULTILINE':regex.MULTILINE,
        'IGNORECASE':regex.IGNORECASE,
        # TODO: there are more
        }
    def unflag(f:str)->int:
        """
        decipher a string value of a regex flag
        """
        return unflags.get(f.rsplit('.',1)[-1].upper(),0)
    def compileTheThing(
        reStr:str,
        flags:typing.Union[int,str,typing.Iterable[str]]=0):
        """
        helper function to compile a thing
        """
        regexp=''.join([line.strip() for line in regexp.split('\n')])
        if isinstance(flags,int):
            pass
        elif isinstance(flags,str):
            flags=unflag(flags)
        else:
            ff:typing.Iterable[str]=flags
            flags=0
            for f in ff:
                flags=~unflag(f)
        return regex.compile(regexp,flags)
    if isinstance(regexp,str):
        return compileTheThing(regexp,flags)
    return regexp


class ReResultTreeNode:
    """
    a single match in a regex tree

    (This is intended to b e created by calling reTrees() )
    """

    def __init__(self,name,value,regexp,dataLocation):
        self._name=name
        self._regexp=regexp
        self._dataLocation=dataLocation
        self._value=value
        self.children:typing.Union[str,typing.Dict[
            str,
            typing.Union[
                "ReResultTreeNode",
                typing.List["ReResultTreeNode"]]]]=value

    def _addUnaccountedValues(self,unaccountedValueName="value"):
        """
        used to create an automatic "value" member in children
        (recursively called on all children)

        if the children do not consume all of this item,
        children["value"] is the value of the entire match
        """
        if isinstance(self.children,Mapping):
            for c in self:
                if isinstance(c,ReResultTreeNode):
                    c._addUnaccountedValues() # noqa: E501 # pylint: disable=line-too-long,protected-access
            if unaccountedValueName not in self.children:
                contig=self.contiguiousChildRange
                if contig is None \
                    or contig[0]!=self._dataLocation[0] \
                    or contig[1]!=self._dataLocation[1]:
                    #
                    self.children[unaccountedValueName]=self._value

    @property
    def contiguiousChildRange(self):
        """
        bump all the children together and get the range

        returns None if not all children are touching
        returns dataLocation if there are no children
        """
        if isinstance(self.children,str) or not self.children:
            return self._dataLocation
        allChildren=list(iter(self))
        allChildren.sort(key=lambda c: c._dataLocation[0]) # noqa: E501 # pylint: disable=line-too-long,protected-access
        last=None
        for c in allChildren:
            if last is None:
                last=c._dataLocation[1]-1 # noqa: E501 # pylint: disable=line-too-long,protected-access
            elif last!=c._dataLocation[0]: # noqa: E501 # pylint: disable=line-too-long,protected-access
                print(f'discontinuity from position {last} to {c._dataLocation[0]}') # noqa: E501 # pylint: disable=line-too-long,protected-access
                return None
            else:
                last=c._dataLocation[1]-1 # noqa: E501 # pylint: disable=line-too-long,protected-access
        return (allChildren[0]._dataLocation[0],last) # noqa: E501 # pylint: disable=line-too-long,protected-access

    @property
    def name(self):
        """
        name of this node in the tree
        """
        return self._name

    def __iter__(self)->typing.Generator["ReResultTreeNode",None,None]:
        """
        iterate over all child ReResultTreeNode objects
        """
        if isinstance(self.children,str):
            return
        for items in self.children.values():
            if isinstance(items,ReResultTreeNode):
                yield items
            else:
                for item in items:
                    yield item

    def append(self,item:"ReResultTreeNode")->None:
        """
        if the named item does not exist, simply add it
        if there already is one, break into a list and add it
        """
        if isinstance(self.children,str):
            self.children={}
        items=self.children.get(item.name,None)
        if items is None:
            self.children[item.name]=item
        elif isinstance(items,Iterable) and not isinstance(items,str):
            items.append(item)
            self.children[item.name]=items
        else:
            items=[items]
            items.append(item)
            self.children[item.name]=items

    @property
    def json(self):
        """
        get this as a json string
        """
        return json.dumps(self.jsonObj)

    @property
    def jsonObj(self):
        """
        get this as a json-compatible object
        """
        def jsonFix(something,asObj=True):
            if isinstance(something,str):
                return something
            if isinstance(something,Iterable):
                return [jsonFix(s,False) for s in something]
            if isinstance(something,Mapping):
                ret={}
                for k,v in something.items():
                    ret[k]=jsonFix(v,False)
                return ret
            if asObj:
                return {something.name:jsonFix(something.children,False)}
            return jsonFix(something.children,False)
        return jsonFix(self)

    def __repr__(self):
        return self.json


def reTrees(
    data:str,
    regexp:typing.Union[typing.Pattern,str],
    flags:typing.Union[int,str,typing.Iterable[str]]=0,
    unaccountedValueName:typing.Optional[str]=None
    )->typing.Generator[ReResultTreeNode,None,None]:
    r"""
    takes data, applies a regex, yieds a series json-compatable dict+list trees

    (Unfortunately, the builtin re library is not quite smart enough, so you'll
    need to pip install its slated replacement https://pypi.org/project/regex/)

    caveats:
        1) regex only captures on named groups
        2) if there is more than one top-level group, they will be combined
            into one object
        3) TODO: when a matching group is constrained to a numeric, will cast
            all matches to a numeric

    :data: the data to parse
    :regexp: a string or regular expression
    :flags: an int, a flag name as a string, or a series of string flag names.
    :unaccountedValueName: if specified, will add unaccounted for characters
        to a value of this name that is, when there are stray capture items,
        a unaccountedValueName called womething like "value"
        can be added
            eg "(?P<number>[0-9](?P<decimal>\.[0-9])?)"
            given "5.4"
            will result in number['decimal']='.4' and
            auto-named number['value']="5.4"
    """
    regexp=refix(regexp,flags)
    def _combineItemsIntoTree(items:typing.List[ReResultTreeNode]
        )->ReResultTreeNode:
        """
        takes a set of items wherein a parent item always
        encloses entirely its child items (no overlapping)

        also assumes that if two items are the exact same location, the second
        is inside the first

        NOTE: items will be sorted by size, so if you don't want that, send
            in a copy

        Returns one or more trees of items.
        """
        retTrees:typing.List[ReResultTreeNode]=[]
        # start with the largest items because they will have to be
        # our top level
        items.sort(
            key=lambda item: item._dataLocation[1]-item._dataLocation[0], # noqa: E501 # pylint: disable=line-too-long,protected-access
            reverse=True)
        def addify(item:ReResultTreeNode,toChildren):
            for c in toChildren:
                if item._dataLocation[0]>=c._dataLocation[0] and item._dataLocation[0]<c._dataLocation[1]: # noqa: E501 # pylint: disable=line-too-long,protected-access
                    #
                    addify(item,c)
                    return
            toChildren.append(item)
        for item in items:
            addify(item,retTrees)
        if not retTrees:
            return ReResultTreeNode('','',items[0]._regexp,(0,0)) # noqa: E501 # pylint: disable=line-too-long,protected-access
        if unaccountedValueName is not None:
            for t in retTrees:
                t._addUnaccountedValues(unaccountedValueName) # noqa: E501 # pylint: disable=line-too-long,protected-access
        if len(retTrees)==1:
            return retTrees[0]
        # otherwise, create an unnamed root
        dataLocation=(
            min([item._dataLocation[0] for item in retTrees]), # noqa: E501 # pylint: disable=line-too-long,protected-access
            max([item._dataLocation[1] for item in retTrees])) # noqa: E501 # pylint: disable=line-too-long,protected-access
        retTreesDict={}
        for item in retTrees:
            retTreesDict[item.name]=item
        return ReResultTreeNode(
            '',retTreesDict,retTrees[0]._regexp,dataLocation) # noqa: E501 # pylint: disable=line-too-long,protected-access
    for m in regexp.finditer(data):
        ret=[]
        # NOTE: if capturesdict() and/or spans() is missing, it is because it
        # was added in regex 2022.9.13 please do a "pip install regex"
        for i,g in enumerate(m.capturesdict().items()):
            name=g[0]
            spans=m.spans(i+1)
            for j,value in enumerate(g[1]):
                node=ReResultTreeNode(name,value,regexp,spans[j])
                ret.append(node)
        yield _combineItemsIntoTree(ret)


def cmdline(args):
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    if not args:
        printhelp=True
    else:
        regexp=None
        flags=0
        unaccountedValueName=None
        for arg in args:
            if arg.startswith('-'):
                arg=[a.strip() for a in arg.split('=',1)]
                arg[0]=arg[0].lower()
                if arg[0] in ['-h','--help']:
                    printhelp=True
                elif arg[0] in ('--re','--regex','--regexp'):
                    if len(arg)<2 or not arg[1]:
                        regexp=None
                    else:
                        regexp=arg[1]
                elif arg[0]=='--flags':
                    if len(arg)<2 or not arg[1]:
                        flags=0
                    else:
                        flags=[s.strip() for s in arg[1].split(',')]
                elif arg[0]=='--unaccountedValueName':
                    if len(arg)<2 or not arg[1]:
                        unaccountedValueName=None
                    else:
                        unaccountedValueName=arg[1]
                elif arg[0]=='--test':
                    testre=r"""
                        (?P<person>(?P<name>[a-z]+)=(?P<numbers>(\s*(?P<number>[-0-9]+(?P<decimal>\.[0-9]+)?))*))
                        """
                    testdata="""bob=1 2.5 3 gloria=4 fred=21 7"""
                    for item in reTrees(testdata,testre):
                        print(item)
                else:
                    print('ERR: unknown argument "'+arg[0]+'"')
            else:
                if regexp is None:
                    print('ERR: you must specify a regular expression!')
                else:
                    for t in reTrees(arg,regexp,flags,unaccountedValueName):
                        print(t)
    if printhelp:
        print('Usage:')
        print('  reTrees.py [options] [data to decode] [more to decode...]')
        print('Options:')
        print('   --test')
        print('   --regexp= ............... regular expression to use')
        print('   --re= ................... same as regexp')
        print('   --regex= ................ same as regexp')
        print('   --flags=flag[,flag] ..... regex flags (such as re.IGNORECASE)') # noqa: E501 # pylint: disable=line-too-long
        print('   --unaccountedValueName= . value name for groups with unaccounted for values') # noqa: E501 # pylint: disable=line-too-long
        print('Note:')
        print('   All options are evaluated in order, making some pretty')
        print('   sophisticated results possible.')
        return -1
    return 0


if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))
