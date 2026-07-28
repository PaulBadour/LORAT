import requests
from bs4 import NavigableString, BeautifulSoup as bs
import random as r
import os
from pathlib import Path
import hashlib
import os
import argparse
import time
import sys
import functools

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test", help="Lists all rules once, test style", action="store_true")
parser.add_argument("-c", "--cache", help="Allows File caching", action="store_true")
parser.add_argument("-f", "--first", type=int, default=1, help="Starting page inclusive, default 1")
parser.add_argument("-l", "--last", type=int, default=-1, help="End page inclusive, default -1, meaning all pages after first")
parser.add_argument("-d", "--depth", type=int, default=5, help="Depth of rules scanned. 1 being only page titles, 5 being all sub rules. Defualt 5")
parser.add_argument("-m", "--delimiter", type=str, default=" -> ", help="Delimiter for displaying levels of rule hierarchy")
args = parser.parse_args()

ROOT_URL = 'https://www.therootdatabase.com/'
TOC_URL = 'https://www.therootdatabase.com/law-of-root/en/'

HIERARCHY_DELIMITER = args.delimiter

FIRST_PAGE = args.first
LAST_PAGE = args.last

# 1 to 5, 5 being all subsub rules also
DEPTH = args.depth

# caching does not currently fully work
CACHING = False

if CACHING:
    CACHE_DIR = Path("cache")
    CACHE_DIR.mkdir(exist_ok=True)

@functools.cache
def getSoup(link):
    if CACHING and link == TOC_URL:
        filename = hashlib.md5(link.encode()).hexdigest() + ".html"
        cache_file = CACHE_DIR / filename
    
        if cache_file.exists():
            # print('loading from cache')
            return bs(cache_file.read_text(encoding="utf-8"), "lxml")

        # print('Saving')
        r = bs(requests.get(link).content, "lxml")
        cache_file.write_text(r.prettify(), encoding="utf-8")
        return r
       
    return bs(requests.get(link).content, "lxml")

def cleanTag(tag):
    if tag.string:
        return tag.string

    string = ""

    for i in tag.contents:
        if i is NavigableString:
            string += i
        else:
            string += cleanTag(i)
    return string

def formatRule(r, table=None):
    split = r.index(' ')
    code = r[:split]
    if code[-1] == '.':
        code = code[:-1]
    desc = r[split + 1:]
    if desc[-1] == '.':
        desc = desc[:-1]

    if '.' not in code:
        return code, desc

    parentCode = code[:code.rfind('.')]
    return code, f"{table[parentCode]}{HIERARCHY_DELIMITER}{desc}"

def buildTable():
    ruleTable = {}
    
    toc = getSoup(TOC_URL)
    headers = toc.find_all('h2', class_='root-title')[1:]

    for idx, i in enumerate(headers):
        if i.string[0] == 'A':
            headers = headers[:idx]
            break

    if LAST_PAGE != -1 and LAST_PAGE < len(headers):
        headers = headers[:LAST_PAGE]
    
    if FIRST_PAGE > 1:
        headers = headers[FIRST_PAGE - 1:]

    if len(headers) == 1 and DEPTH == 1:
        print('nerd')
        sys.exit()

    links = []
    for i in headers:
        link = i.parent.parent.parent.get('href')
        links.append(link)


    for l in links:
        soup = getSoup(f"{ROOT_URL}{l}")
        
        # Main header
        k, v = formatRule(cleanTag(soup.find('h2')))
        ruleTable[k] = v.strip()

        if DEPTH < 2:
            continue

        # Secondry headers
        titles = soup.find_all('h4')
        for t in titles:
            k, v = formatRule(cleanTag(t), ruleTable)
            ruleTable[k] = v.strip()

        if DEPTH < 3:
            continue

        labels = soup.find_all('span', class_='law-code')
        lastRule = None
        lastSubRule = None
        for i in labels:
            # Sub rule
            if not any(char.isdigit() for char in i.string):
                if DEPTH < 4:
                    continue
                # 4 deep subrule
                if i.string[0].isupper():
                    code = f'{lastRule}.{i.string.strip()}'
                    desc = i.find_next_sibling().strong.string
                    k, v = formatRule(f"{code} {desc}", ruleTable)
                    ruleTable[k] = v.strip()
                    lastSubRule = code
                # 5 deep subsubrule
                elif DEPTH == 5:
                    code = f'{lastSubRule}.{i.string.strip()}'
                    desc = i.find_next_sibling().strong.string
                    k, v = formatRule(f"{code} {desc}", ruleTable)
                    ruleTable[k] = v.strip()
            # Main Rule
            else:
                code = i.string
                desc = cleanTag(i.parent.find_next_sibling().strong)
                k, v = formatRule(f"{code} {desc}", ruleTable)
                ruleTable[k] = v.strip()
                lastRule = code

    return ruleTable

if __name__ == '__main__':
    print('Loading Table...')
    table = buildTable()

    lastLine = None
    lastCode = None
    inp = None
    code = None
    testList = None
    done = 1
    while inp != 'q':
        os.system('cls' if os.name == 'nt' else 'clear')
        if lastLine:
            if args.test:
                lastLine = f"{lastLine} [{done} / {len(testList)}]"
            print(lastLine)
        while code == lastCode:
            if args.test:
                if not testList:
                    testList = list(table.keys())
                    r.shuffle(testList)
                    code = testList[0]
                else:
                    nextInd = testList.index(lastCode) + 1
                    done += 1
                    if nextInd >= len(testList):
                        code = 'Done!'
                    else:
                        code = testList[nextInd]
            else:
                code = r.choice(list(table.keys()))
        lastCode = code
        inp = input(f'{code}: ')
        if inp == 'r':
            lastLine = None
            lastCode = None
            inp = None
            code = None
            testList = None
            continue
        if code == "Done!":
            break
        lastLine = f"{code}: {table[code]}"
    os.system('cls' if os.name == 'nt' else 'clear')