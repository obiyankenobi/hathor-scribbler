import argparse
import os
import requests
import sys
import time
import urllib.parse

from typing import TYPE_CHECKING, Any, NamedTuple, Optional
from inspect import currentframe, getframeinfo


BASE_URL = 'http://localhost:PORT/'
WALLET_ID = '_id'
HEADERS = { 'X-Wallet-Id': WALLET_ID }
NETWORK = 'mainnet'
FIRST_ADDRESS = None

class Token(NamedTuple):
    name: str
    symbol: str
    uid: str


# TODO add docstring to all methods
# TODO add types to all methods
# TODO proper logging: https://docs.python.org/3/howto/logging.html
# TODO check HTR balance

def print_debug(*args, **kwargs) -> None:
    if DEBUG: print(*args, **kwargs)

def get_wallet_endpoint(command: str) -> str:
    endpoints = {
        'start': '/start',
        'status': '/wallet/status',
        'balance': '/wallet/balance',
        'addresses': '/wallet/addresses',
        'send': '/wallet/send-tx',
        'create-nft': '/wallet/create-nft'
    }
    return urllib.parse.urljoin(BASE_URL, endpoints[command])

def get_wallet_service_endpoint(address: str) -> str:
    #https://explorer-service.mainnet.hathor.network/address/tokens?address=HRkMF9CuwdCvqat8voBcb3a2bjRiRfRPBX&limit=50
    #https://explorer-service.testnet.hathor.network/address/tokens?address=HRkMF9CuwdCvqat8voBcb3a2bjRiRfRPBX&limit=50
    return 'https://explorer-service.{}.hathor.network/address/tokens?address={}&limit=50'.format(NETWORK, address)

def check_wallet_status() -> str:
    try:
        r = requests.get(get_wallet_endpoint('status'), headers = HEADERS)
        if r.status_code != 200:
            sys.exit(-1)
        
        resp = r.json()
        # If the wallet is not started, the 'success' key will be set to False.
        # If it's started, there's will be no 'success' key and we can get the 
        # 'statusMessage' key
        print_debug('check_wallet_status', resp)
        if 'success' in resp and not resp['success']:
            # wallet not started
            print_debug('check_wallet_status not started')
            return 'Not started'
        elif 'statusMessage' in resp:
            global NETWORK
            NETWORK = resp['network']
            print_debug('check_wallet_status started', resp)
            return resp['statusMessage']
        else:
            print('Unknown wallet status, exiting')
            sys.exit(-1)

    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)

def is_wallet_ready() -> bool:
    return check_wallet_status() == 'Ready'


def _get_addresses() -> list[str]:
    try:
        r = requests.get(get_wallet_endpoint('addresses'), headers = HEADERS)
        if r.status_code != 200:
            sys.exit(-1)
        
        resp = r.json()
        return resp['addresses']

    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)


def _get_tokens(address: str) -> list[str]:
    print_debug('get tokens for address', address)
    #print('endpoint', get_wallet_service_endpoint(address))
    try:
        r = requests.get(get_wallet_service_endpoint(address))
        if r.status_code != 200:
            sys.exit(-1)
        # Expected reply
        # {
        #  "total": 1,
        #  "tokens": {
        #    "00001316b675b667970b8dfce5a8af0999771d11101d97f7b929250be64e62f8": {
        #      "token_id": "00001316b675b667970b8dfce5a8af0999771d11101d97f7b929250be64e62f8",
        #      "name": "EasyToken24102555A1",
        #      "symbol": "EASY"
        #    }
        #  }
        # }
        resp = r.json()
        return resp['tokens']

    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)


def get_tokens():
    tokens = {}
    addresses = _get_addresses()
    # TODO to speed up
    #addresses = _get_addresses()[:3]
    global FIRST_ADDRESS
    FIRST_ADDRESS = addresses[0]

    for address in addresses:
        # merge the dicts
        tokens |= _get_tokens(address)
        # sleep so we don't hit the API rate limit, as we are fetching from remote endpoint
        time.sleep(0.5)
    
    # use Token namedtuple
    for uid, token in tokens.items():
        t = Token(token['name'], token['symbol'], uid)
        tokens[uid] = t
    # we don't save HTR token
    tokens.pop('00', None)
    return list(tokens.values())


def _print_tokens(tokens):
    count = 0
    print('Symbol, name, uid')
    for t in tokens:
        count += 1
        print('{}: {}, {}, {}'.format(count, t.symbol, t.name, t.uid))


def _store_info(info: str, token_uid: str, address: str) -> bool:
    payload = { 'outputs': [
            { 'type': 'data', 'data': info },
            { 'address': address, 'value': 1, 'token': token_uid }
        ]
    }
    print_debug('_store_info payload', payload)
    try:
        r = requests.post(get_wallet_endpoint('send'), headers = HEADERS, json = payload)
        if r.status_code != 200:
            print_debug('_store_info exit', r.status_code, r.text)
            sys.exit(-1)
        
        resp = r.json()
        if not resp['success']:
            print('Error sending transaction', resp)
            return False
        else:
            print('Successfully stored, tx hash', resp['hash'])
            return True
        
    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)


def add_new_entry(tokens):
    _print_tokens(tokens)
    choice = int(input('Add to which token? '))
    token = tokens[choice - 1]
    # TODO it would be nice to show the last N entries from this tokens
    info = input('What information shall be stored? ')
    print('Storing on token {} ({}) the following information: {}'.format(token.name, token.symbol, info))
    
    confirm = input("Confirm [y/n]?")
    
    if confirm == 'y':
        _store_info(info, token.uid, FIRST_ADDRESS)
    elif confirm == 'n':
        print('Operation aborted')
    else:
        print('Unknown path')


def _create_token(name: str, symbol:str, info: str):
    payload = { 'name': name, 'symbol': symbol, 'amount': 1, 'data': info, 'address': FIRST_ADDRESS , 'change_address': FIRST_ADDRESS }
    print_debug('_create_token payload', payload)
    try:
        r = requests.post(get_wallet_endpoint('create-nft'), headers = HEADERS, json = payload)
        if r.status_code != 200:
            print_debug('_create_token exit', r.status_code, r.text)
            sys.exit(-1)
        
        resp = r.json()
        if not resp['success']:
            print('Error creating token', resp)
            return None
        else:
            uid = resp['hash']
            print('Successfully created token', uid)
            return Token(name, symbol, uid) 

    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)

def create_token():
    symbol = input('What\'s the token symbol? ')
    name = input('What\'s the token name? ')
    info = input('What\'s the initial information to be stored? ')
    print('Name:', name)
    print('Symbol:', symbol)
    print('Information:', info)
    
    confirm = input("Confirm [y/n]?")
    
    if confirm == 'y':
        return _create_token(name, symbol, info)
    elif confirm == 'n':
        print('Operation aborted')
    else:
        print('Unknown path')


def start_wallet(seed: str) -> None:
    print('Starting wallet at {} with seed {}'.format(BASE_URL, seed))
    payload = {'wallet-id': WALLET_ID, 'seedKey': seed}
    try:
        r = requests.post(get_wallet_endpoint('start'), data = payload)
        if r.status_code != 200:
            sys.exit(-1)
        
        resp = r.json()
        if resp['success']:
            print('Wallet started')
            time.sleep(2)
        elif resp['errorCode'] == 'WALLET_ALREADY_STARTED':
            print('Wallet already started')
        else:
            print('Unhandled error starting wallet', resp['errorCode'])
            sys.exit(-1)
        
        # wait for wallet to load
        ready = False
        while not ready:
            status = check_wallet_status()
            if status == 'Ready':
                print('Wallet ready')
                ready = True
            elif status == 'Error':
                print('Error loading wallet')
                sys.exit(-1)
            else:
                print('Wallet not ready. Waiting...')
                time.sleep(2)

    except Exception as err:
        frameinfo = getframeinfo(currentframe())
        print('ERROR', frameinfo.lineno, err)
        print('Is the wallet headless running?')
        sys.exit(-1)


def main(port: str, seed: str, debug: bool):
    tokens = []
    global BASE_URL, DEBUG
    DEBUG = debug
    BASE_URL = BASE_URL.replace('PORT', port)

    # TODO check if wallet is started
    # set network and first address
    
    while True:
        print('\nWhat would you like to do?')
        print('1. Add new entry to existing tokens')
        print('2. Check existing tokens')
        print('3. Create new token')
        print('4. Start wallet')
        print('5. Check wallet status')
        print('6. Exit')
        choice = int(input("Choose option: "))
        if choice == 1:
            if not is_wallet_ready():
                print('Wallet not ready\n')
                continue
            if not tokens:
                print('Fetching tokens...')
                tokens = get_tokens()
            add_new_entry(tokens)
        elif choice == 2:
            if not is_wallet_ready():
                print('Wallet not ready\n')
                continue
            if not tokens:
                print('Fetching tokens...')
                tokens = get_tokens()
            _print_tokens(tokens)
        elif choice == 3:
            token = create_token()
            if token: tokens.append(token)
            pass
        elif choice == 4:
            start_wallet(seed)
        elif choice == 5:
            print('Wallet status:', check_wallet_status())
        elif choice == 6:
            print('See you soon!')
            break
        else:
            print('Invalid option\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', nargs='?', default='8000')
    parser.add_argument('--seed', nargs='?', default='default')
    parser.add_argument('--debug', default=False, action='store_true')
    args = parser.parse_args()
    main(args.port, args.seed, args.debug)
