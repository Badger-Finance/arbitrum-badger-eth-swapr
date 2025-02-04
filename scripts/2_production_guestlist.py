import time

from brownie import (
    accounts,
    network,
    AdminUpgradeabilityProxy,
    VipCappedGuestListWrapperUpgradeable,
    BadgerRegistry,
    SettV4,
)

from config import REGISTRY

from helpers.constants import AddressZero

import click
from rich.console import Console

console = Console()

sleep_between_tx = 1


def main():
    """
    FOR PRODUCTION
    Deploys a guestlist contract, sets its parameters and assigns it to an specific vault.
    Additionally, the script transfers the guestlist's ownership to the Badger Governance.
    IMPORTANT: Must input the desired vault address to add the guestlist to as well as the
    different guestlist parameters below.
    """

    # NOTE: Input your vault address and guestlist parameters below:
    vaultAddr = "0xE9C12F06F8AFFD8719263FE4a81671453220389c"
    merkleRoot = "0x0000000000000000000000000000000000000000000000000000000000000000"
    userCap = 2 ** 256 - 1
    totalCap = 3040334965383509340000

    # Get deployer account from local keystore. Deployer must be the
    # vault's governance address in order to set its guestlist parameters.
    dev = connect_account()

    # Get actors from registry
    registry = BadgerRegistry.at(REGISTRY)

    governance = registry.get("governance")
    proxyAdmin = registry.get("proxyAdminTimelock")

    assert governance != AddressZero
    assert proxyAdmin != AddressZero

    # Deploy guestlist
    guestlist = deploy_guestlist(dev, proxyAdmin, vaultAddr)

    # Set guestlist parameters
    guestlist.setUserDepositCap(userCap, {"from": dev})
    assert guestlist.userDepositCap() == userCap

    guestlist.setTotalDepositCap(totalCap, {"from": dev})
    assert guestlist.totalDepositCap() == totalCap

    guestlist.setGuestRoot(merkleRoot, {"from": dev})
    assert guestlist.guestRoot() == merkleRoot

    # Transfers ownership of guestlist to Badger Governance
    # guestlist.transferOwnership(governance, {"from": dev})
    # assert guestlist.owner() == governance

    # Sets guestlist on Vault (Requires dev == Vault's governance)
    vault = SettV4.at(vaultAddr)
    vault.setGuestList(guestlist.address, {"from": dev})


def deploy_guestlist(dev, proxyAdmin, vaultAddr):

    guestlist_logic = VipCappedGuestListWrapperUpgradeable.at(
        "0x6DC573500b689f7972D5544809ae2DFC5CF143B5"
    )  # Guestlist Logic

    # Initializing arguments
    args = [vaultAddr]

    guestlist_proxy = AdminUpgradeabilityProxy.deploy(
        guestlist_logic,
        proxyAdmin,
        guestlist_logic.initialize.encode_input(*args),
        {"from": dev},
        publish_source=True,
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(guestlist_proxy)
    guestlist_proxy = VipCappedGuestListWrapperUpgradeable.at(guestlist_proxy.address)

    console.print("[green]Guestlist was deployed at: [/green]", guestlist_proxy.address)

    return guestlist_proxy


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
