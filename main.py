import base58
import logging
import time
import re
import os
import sys
import json
import websockets
import asyncio

import datetime

from solders.keypair import Keypair
from solders.signature import Signature
from solders.pubkey import Pubkey

from solana.rpc.api import Client
from solana.rpc.commitment import Commitment

from configparser import ConfigParser
from threading import Thread, Event

# Other Methods created
from amm_selection import select_amm2trade
from utils.new_pools_list import add
from utils.webhook import sendWebhook
from loadkey import load_keypair_from_file
from raydium.new_pool_address_identifier import get_pair_address_new_pool
import threading

os.system(F"pkill -f {sys.argv[0]}")
# ------------------------ ------------------------ ------------------------
#  INTIALIZING VARIABLES
# ------------------------ ------------------------ ------------------------
# to read content from config.ini
config = ConfigParser()
seen_signatures = set()
# using sys and os because sometimes this shitty config reader does not read from curr directory
config.read(os.path.join(sys.path[0], 'data', 'config.ini'))

# Configuring the logging
log_file = os.path.join('data', f"logs.txt")
logging.basicConfig(level=logging.WARNING, filename=log_file,
                    format='%(asctime)s|%(name)s|%(levelname)s|%(message)s', datefmt='%d-%b-%y %I:%M:%S %p')


def custom_exception_handler(exc_type, exc_value, exc_traceback):
    # Log the exception automatically
    logging.exception("An unhandled exception occurred: %s", str(exc_value))

sys.excepthook = custom_exception_handler

# Infura settings - register at infura and get your mainnet url.
RPC_HTTPS_URL = config.get("RPC_URL", "rpc_url")

# Wallets private key
private_key = config.get("WALLET", "private_key")
wallet_address = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# Check if private key is in the form of ./something.json
if re.match(r'\w+\.json', private_key):
    # Private key is in the form of ./something.json
    payer = load_keypair_from_file(private_key)
else:
    # Private key is a long string
    payer = Keypair.from_bytes(base58.b58decode(private_key))

# Solana Client Initialization
# solana_client = Client(RPC_HTTPS_URL, commitment=Commitment(
#     "confirmed"), timeout=10, blockhash_cache=True)
solana_client = Client(RPC_HTTPS_URL)
event_thread = Event()

# ------------------------ ------------------------ ------------------------
#  INTIALIZATION END
# ------------------------ ------------------------ ------------------------

# Load Previous Coins: ---------------------------
# file_path = os.path.join(sys.path[0], 'data', 'bought_tokens_info.json')

# Load the JSON file
# with open(file_path, 'r') as file:
#     data = json.load(file)

# if len(data) > 0:
#     for token in data:
#         # Call select_amm2trade token method.
#         Thread(target=select_amm2trade, name=token, args=(
#             token, payer, solana_client, event_thread)).start()
#         event_thread.wait()
#         event_thread.clear()

def getTokens(str_signature):
    try:
        signature = Signature.from_string(str_signature)
        transaction = solana_client.get_transaction(signature, encoding="jsonParsed",max_supported_transaction_version=0).value
        instruction_list = transaction.transaction.transaction.message.instructions
        for instructions in instruction_list:
            print('---instructions.program_id--- : ', instructions.program_id)
            if instructions.program_id == Pubkey.from_string(wallet_address):
                now = datetime.datetime.now()
                print("============NEW POOL DETECTED====================\n",now)
                token_buy = False
                if instructions.accounts[8] == 'So11111111111111111111111111111111111111112':
                    token_buy = instructions.accounts[9]
                else:
                    token_buy = instructions.accounts[8]

                print("Token find : ",instructions.accounts[8], instructions.accounts[9])
                print("Token buy : ",token_buy)
                Thread(target=select_amm2trade, name='EnGV1WN7X9nQujfJtaZHGEjb4iw2CasqoCk51xeNHJ7k', args=('EnGV1WN7X9nQujfJtaZHGEjb4iw2CasqoCk51xeNHJ7k', payer, solana_client, event_thread)).start()
                event_thread.wait()
                event_thread.clear()
    except Exception as e:
       # By this way we can know about the type of error occurring
        print("Get tokens error is: ", e)
          
async def run():
   uri = "wss://api.mainnet-beta.solana.com"
   async with websockets.connect(uri) as websocket:
       # Send subscription request
       await websocket.send(json.dumps({
           "jsonrpc": "2.0",
           "id": 1,
           "method": "logsSubscribe",
           "params": [
               {"mentions": [wallet_address]},
               {"commitment": "finalized"}
           ]
       }))

       first_resp = await websocket.recv()
       response_dict = json.loads(first_resp)
       if 'result' in response_dict:
          print("Subscription successful. Subscription ID: ", response_dict['result'])

       # Continuously read from the WebSocket
       async for response in websocket:
           response_dict = json.loads(response)
           if response_dict['params']['result']['value']['err'] == None :
               signature = response_dict['params']['result']['value']['signature']
               if signature not in seen_signatures:
                  seen_signatures.add(signature)
                  log_messages_set = set(response_dict['params']['result']['value']['logs'])

                  search="initialize2"
                  if any(search in message for message in log_messages_set):
                      print(f"Transaction: https://solscan.io/tx/{signature}")
                      getTokens(signature)
           else:
               pass

async def main():
    await run()

asyncio.run(main())