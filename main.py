import questionary
from client import Client
import asyncio
import json
from web3.contract import AsyncContract
from token_data import token_data

private_key = "YOUR_PRIVATE_KEY"


def main():
    chain_name = questionary.select(
        f"\n Выберите сеть\n",
        choices=["Arbitrum One", "Optimism", "Arbitrum Sepolia", "BSC"],
    ).ask()

    coin = questionary.select(
        f"\n Выберите токен\n",
        choices=["USDT", "USDC", "DAI", "LINK"],
    ).ask()

    try:
        amount = float(
            input(
                "Введите кол-во токенов для отправки - или введите 0 чтобы отправить 100% токенов: "
            )
        )
    except ValueError:
        print("Ошибка: Кол-во должно быть числом")
        return
    recipient_address = input("Введите адрес получателя: ")
    asyncio.run(
        transfer_ERC20(
            chain_name, coin, amount_to_send=amount, recipient_address=recipient_address
        )
    )


async def transfer_ERC20(chain_name, coin, amount_to_send, recipient_address):
    client = Client(private_key, chain_name=chain_name)

    try:
        with open(
            f'C:/pudge/ERC_TRANSFER/abi/{token_data[chain_name][coin]["ABI_URL"]}', "r"
        ) as file:
            contract_abi = json.load(file)
    except FileNotFoundError:
        print(f"Ошибка: Не удалось найти ABI для токена {coin} в сети {chain_name}")
        return

    try:
        checksum_address = client.w3.to_checksum_address(recipient_address)
    except ValueError:
        print("Ошибка: Вы указали неверный адрес получателя")
        return

    token_contract: AsyncContract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(token_data[chain_name][coin]["contract"]),
        abi=contract_abi,
    )
    decimals = await token_contract.functions.decimals().call()
    balance = await token_contract.functions.balanceOf(client.address).call()
    converted_amount = (
        balance  ## отправляем 100 процентов токена
        if amount_to_send == 0
        else client.to_wei_custom(  ## отправляем указанное кол-во
            amount_to_send, decimals
        )
    )

    tx_params = await client.generate_tx()
    transaction = await token_contract.functions.transfer(
        checksum_address, converted_amount
    ).build_transaction(tx_params)

    tx_hash_hex = await client.sign_and_send_tx(transaction)

    await client.wait_tx(tx_hash_hex)


if __name__ == "__main__":
    main()
