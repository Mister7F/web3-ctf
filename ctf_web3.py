from web3 import Web3 as _Web3
from solcx import (
    compile_source as _compile_source,
    install_solc as _install_solc,
    get_installable_solc_versions as _get_installable_solc_versions,
)


class Account:
    def __init__(self, public: str, private: str):
        assert int(public, 16) < int(private, 16)
        self.public = _Web3.to_checksum_address(public)
        self.private = private


class Web3:
    def __init__(self, url: str, account: Account):
        # anvil: http://localhost:8545
        # sepolia: https://rpc2.sepolia.org
        self.url = url
        self.account = account
        self.w3 = _Web3(_Web3.HTTPProvider(url))
        self.w3.eth.default_account = account.public
        assert self.w3.is_connected()

    def get_balance(self) -> int:
        return self.w3.eth.get_balance(self.account.public)

    def transfer(self, value: int, destination: str):
        nonce = self.w3.eth.get_transaction_count(self.account.public)
        gas_price = float(self.w3.from_wei(self.w3.eth.gas_price, "ether"))
        allowed_gas = int(0.0005 / gas_price)
        tx = {
            "nonce": nonce,
            "to": destination,
            "value": value,
            "gasPrice": self.w3.eth.gas_price,
            "gas": allowed_gas,
        }
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.private)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def compile(
        self, source: str, version: str = "0.8.0"
    ) -> list["ContractDefinition"]:
        _install_solc(version)
        compiled_sol = _compile_source(
            f"""
            //SPDX-License-Identifier: UNLICENSED
            pragma solidity ^{version};
            {source}
            """,
            output_values=["abi", "bin"],
            solc_version=version,
        )

        contracts: list[ContractDefinition] = []
        while compiled_sol:
            contract_id, contract_interface = compiled_sol.popitem()
            bytecode = contract_interface["bin"]
            abi = contract_interface["abi"]
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            contracts.append(ContractDefinition(self, contract))
        return contracts


class Contract:
    def __init__(self, web3, address: str, abi):
        address = _Web3.to_checksum_address(address)
        self.web3 = web3
        self.address = address
        self.contract = web3.w3.eth.contract(address=address, abi=abi)

    def call(self, method: str, *args):
        return getattr(self.contract.functions, method)(*args).call()

    def call_transaction(self, method: str, *args, value: int = 0):
        w3 = self.web3.w3
        nonce = w3.eth.get_transaction_count(self.web3.account.public)
        Chain_id = w3.eth.chain_id
        transaction = getattr(self.contract.functions, method)(*args).build_transaction(
            {
                "chainId": Chain_id,
                "from": self.web3.account.public,
                "nonce": nonce,
                "value": value,
            }
        )
        signed_tx = w3.eth.account.sign_transaction(
            transaction,
            private_key=self.web3.account.private,
        )
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return w3.eth.wait_for_transaction_receipt(tx_hash)


class ContractDefinition:
    def __init__(self, web3: Web3, w3_contract):
        self.web3 = web3
        self.w3 = web3.w3
        self.w3_contract = w3_contract

    def get_published(self, address: str) -> Contract:
        """ "From the definition of the contract and its address, return the contract itself."""
        return Contract(self.web3, address, self.w3_contract.abi)

    def publish(self, *args) -> "Contract":
        """Consume credit to publish the contract."""
        nonce = self.w3.eth.get_transaction_count(self.web3.account.public)
        Chain_id = self.w3.eth.chain_id
        transaction = self.w3_contract.constructor(*args).build_transaction(
            {"chainId": Chain_id, "from": self.web3.account.public, "nonce": nonce}
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            transaction,
            private_key=self.web3.account.private,
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return Contract(self.web3, tx_receipt.contractAddress, self.w3_contract.abi)
