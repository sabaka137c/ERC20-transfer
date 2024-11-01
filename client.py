import asyncio
from web3 import AsyncHTTPProvider, AsyncWeb3
from chain_list import ChainList
import random
from web3.exceptions import TransactionNotFound
import sys


class Client:
    def __init__(self, private_key, chain_name) -> None:
        self.private_key = private_key
        self.chain_name = chain_name
        self.scan_url = ChainList.data.get(self.chain_name, {}).get("scan_url", None)
        self.rpc_url = random.choice(ChainList.data[self.chain_name]["RPC"])
        self.is_chain_use_eip1559 = ChainList.data[self.chain_name].get(
            "is_chain_use_eip1559", False
        )

        self.w3 = AsyncWeb3(AsyncHTTPProvider(self.rpc_url))
        self.address = self.w3.to_checksum_address(
            self.w3.eth.account.from_key(self.private_key).address
        )

    async def generate_tx(self):
        base_fee = await self.w3.eth.gas_price
        max_priority_fee_per_gas = await self.w3.eth.max_priority_fee
        max_fee_per_gas = int(base_fee + max_priority_fee_per_gas)

        transaction = {
            "chainId": await self.w3.eth.chain_id,
            "nonce": await self.w3.eth.get_transaction_count(self.address),
            "from": self.address,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "maxFeePerGas": int(max_fee_per_gas * 1.5),
        }

        estimated_gas = await self.w3.eth.estimate_gas(transaction)
        transaction["gas"] = int(estimated_gas * 1.5)
        transaction["type"] = "0x2"
        return transaction

    async def sign_and_send_tx(self, tx):
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, self.private_key
        ).rawTransaction
        print("Успешно подписал транзакцию")

        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx)
        tx_hash_hex = self.w3.to_hex(tx_hash)
        print(f"Успешно отправил транзикцию: {tx_hash_hex} ")
        return tx_hash_hex

    async def wait_tx(self, tx_hash):
        total_time = 0
        timeout = 120
        poll_latency = 10
        while True:
            try:
                receipts = await self.w3.eth.get_transaction_receipt(tx_hash)
                status = receipts.get("status")
                if status == 1:
                    if self.scan_url:
                        print(
                            f"Транзакция выполнена успешно: {self.scan_url}/tx/{tx_hash}"
                        )
                    else:
                        print(f"Транзакция выполнена успешно: {tx_hash}")
                    return True
                elif status is None:
                    await asyncio.sleep(poll_latency)
                else:
                    print("Транзакция завершилась с ошибкой")
                    return False
            except TransactionNotFound:
                if total_time > timeout:
                    print("Транзакция не найдена")
                    total_time += poll_latency
                    await asyncio.wait(poll_latency)

    async def check_native_balance(self):
        return await self.w3.eth.get_balance(self.address)

    def to_wei_custom(self, number, decimals):

        unit_name = {6: "mwei", 9: "qwei", 18: "ether"}.get(decimals)

        if not unit_name:
            raise RuntimeError(f"Can not find unit name with decimals: {decimals}")

        return self.w3.to_wei(number, unit_name)
