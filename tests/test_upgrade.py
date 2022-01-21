import brownie
import pytest
from brownie import MyStrategy

@pytest.fixture
def strat_proxy(Contract):
    yield Contract.from_explorer("0x22F340C2604Dc1cDBe26caC5838Ea9EBC8862a46")


@pytest.fixture
def proxy_admin(strat_proxy, web3, Contract):
    # ADMIN_SLOT = bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1)
    ADMIN_SLOT = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
    yield Contract(web3.eth.getStorageAt(strat_proxy.address, ADMIN_SLOT)[12:])


def test_upgrade(accounts, interface, strat_proxy, proxy_admin):
    deployer = accounts[0]
    controller = interface.IController(strat_proxy.controller())
    want = interface.IERC20(strat_proxy.want())
    vault = interface.ISett(controller.vaults(want))

    # Verify no pending rewards
    old_staking_contract = interface.IERC20StakingRewardsDistribution(strat_proxy.stakingContract())

    rewards = old_staking_contract.claimableRewards(strat_proxy)
    print(f"Pending rewards: {rewards}")

    for amount in rewards:
        assert amount == 0

    # Verify that withdrawAll is failing
    strat_balance = strat_proxy.balanceOf()
    vault_balance = want.balanceOf(vault)
    assert strat_proxy.balanceOfPool() > 0

    with brownie.reverts("SRD23"):
        strat_proxy.withdrawAll({"from": controller})

    ## Storage layout
    lpComponent = strat_proxy.lpComponent()
    reward = strat_proxy.reward()
    stakingContract = strat_proxy.stakingContract()

    ## Upgrade
    new_logic = MyStrategy.deploy({"from": deployer})
    owner = proxy_admin.owner()
    proxy_admin.upgrade(strat_proxy, new_logic, {"from": owner})
    print(f"Proxy admin: {proxy_admin.address}")
    print(f"Proxy admin owner: {owner}")

    ## Verify storage layout
    assert strat_proxy.lpComponent() == lpComponent
    assert strat_proxy.reward() == reward
    assert strat_proxy.stakingContract() == stakingContract

    # Check withdrawAll works
    strat_proxy.withdrawAll({"from": controller})

    assert strat_proxy.balanceOf() == 0
    assert want.balanceOf(vault) == vault_balance + strat_balance
