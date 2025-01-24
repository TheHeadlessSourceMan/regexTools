r"""
given a string filled with quotes like "she said \"hello\"" extract just
the quote contents

Example:
    allQuotes(r'''
        she said, "hello there"
        he replied, "don't you \"hello there\", me!", to sally''')
    returns
        hello there
        don't you "hello there", me!
"""
import typing


def allQuotes(value,quot='"',delim='\\')->typing.Generator[str,None,None]:
    r"""
    given a string filled with quotes like "she said \"hello\"" extract just
    the quote contents

    Example:
        allQuotes(r'''
            she said, "hello there"
            he replied, "don't you \"hello there\", me!", to sally''')
        returns
            hello there
            don't you "hello there", me!
    """
    inquote=False
    els=value.split(quot)
    cur=[]
    for el in els:
        if inquote:
            if el[-1]==delim:
                cur.append(el[0:-1])
                # still inquote=True!
            else:
                if cur:
                    cur.append(el)
                    yield quot.join(cur)
                    cur=[]
                else:
                    yield el
                inquote=False
        else:
            inquote=True
