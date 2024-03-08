from ctf_web3 import Web3, Account


account = Account(
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
)
web3 = Web3("http://localhost:8545", account)

print(web3.get_balance())

source_victim = """
contract Wallet {
  address public owner;
  bool public locked;

  constructor(address _player)  {
    owner = _player;
    locked = true;
  }

  function Flag() public {
    locked = false;
  }
}
"""

contract = web3.compile(source_victim)[0].publish(account.public)


##########
# ATTACK #
##########


source = (
    source_victim
    + """
contract Attack {
    Wallet wallet;

    constructor(Wallet _wallet) {
        wallet = Wallet(_wallet);
    }

    function attack() external {
        wallet.Flag();
    }

    function ret(uint x) public returns (uint) {
        return 1337 + x;
    }
}
"""
)
contract_attack = web3.compile(source)[1].publish(contract.address)

print(contract_attack.call("ret", 5))
