#!/usr/bin/env python3
# Copyright (c) 2020-2022 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test datacarrier functionality"""
from test_framework.messages import (
    CTxOut,
    MAX_OP_RETURN_RELAY,
)
from test_framework.script import (
    CScript,
    OP_RETURN,
)
from test_framework.test_framework import BitcoinTestFramework
from test_framework.test_node import TestNode
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
)
from test_framework.wallet import MiniWallet

from random import randbytes

# The historical maximum, now used to test coverage
CUSTOM_DATACARRIER_ARG = 83

class DataCarrierTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 5
        self.extra_args = [
            [], # default is uncapped
            ["-datacarrier=0"], # no relay of datacarrier
            ["-datacarrier=1", f"-datacarriersize={CUSTOM_DATACARRIER_ARG}"],
            ["-datacarrier=1", "-datacarriersize=2"],
            ["-datacarrier=1", "-mindatacarriersize=10"], # minimum size of 10 bytes
        ]

    def test_null_data_transaction(self, node: TestNode, data, success: bool) -> None:
        tx = self.wallet.create_self_transfer(fee_rate=0)["tx"]
        data = [] if data is None else [data]
        tx.vout.append(CTxOut(nValue=0, scriptPubKey=CScript([OP_RETURN] + data)))
        tx.vout[0].nValue -= tx.get_vsize()  # simply pay 1sat/vbyte fee

        tx_hex = tx.serialize().hex()

        if success:
            self.wallet.sendrawtransaction(from_node=node, tx_hex=tx_hex)
            assert tx.txid_hex in node.getrawmempool(True), f'{tx_hex} not in mempool'
        else:
            # Error message could be either "datacarrier" or "datacarrier-too-small"
            assert_raises_rpc_error(-26, "datacarrier", self.wallet.sendrawtransaction, from_node=node, tx_hex=tx_hex)

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])

        # Test that bare multisig is allowed by default. Do it here rather than create a new test for it.
        assert_equal(self.nodes[0].getmempoolinfo()["permitbaremultisig"], True)

        assert_equal(self.nodes[0].getmempoolinfo()["maxdatacarriersize"], MAX_OP_RETURN_RELAY)
        assert_equal(self.nodes[1].getmempoolinfo()["maxdatacarriersize"], 0)
        assert_equal(self.nodes[2].getmempoolinfo()["maxdatacarriersize"], CUSTOM_DATACARRIER_ARG)
        assert_equal(self.nodes[3].getmempoolinfo()["maxdatacarriersize"], 2)
        assert_equal(self.nodes[4].getmempoolinfo()["mindatacarriersize"], 10)

        # By default, any size is allowed.

        # If it is custom set to 83, the historical value,
        # only 80 bytes are used for data (+1 for OP_RETURN, +2 for the pushdata opcodes).
        custom_size_data = randbytes(CUSTOM_DATACARRIER_ARG - 3)
        too_long_data = randbytes(CUSTOM_DATACARRIER_ARG - 2)
        extremely_long_data = randbytes(MAX_OP_RETURN_RELAY - 200)
        one_byte = randbytes(1)
        zero_bytes = randbytes(0)

        self.log.info("Testing a null data transaction succeeds for default arg regardless of size.")
        self.test_null_data_transaction(node=self.nodes[0], data=too_long_data, success=True)
        self.test_null_data_transaction(node=self.nodes[0], data=extremely_long_data, success=True)

        self.log.info("Testing a null data transaction with -datacarrier=false.")
        self.test_null_data_transaction(node=self.nodes[1], data=custom_size_data, success=False)

        self.log.info("Testing a null data transaction with a size larger than accepted by -datacarriersize.")
        self.test_null_data_transaction(node=self.nodes[2], data=too_long_data, success=False)

        self.log.info("Testing a null data transaction with a size equal to -datacarriersize.")
        self.test_null_data_transaction(node=self.nodes[2], data=custom_size_data, success=True)

        self.log.info("Testing a null data transaction with no data.")
        self.test_null_data_transaction(node=self.nodes[0], data=None, success=True)
        self.test_null_data_transaction(node=self.nodes[1], data=None, success=False)
        self.test_null_data_transaction(node=self.nodes[2], data=None, success=True)
        self.test_null_data_transaction(node=self.nodes[3], data=None, success=True)

        self.log.info("Testing a null data transaction with zero bytes of data.")
        self.test_null_data_transaction(node=self.nodes[0], data=zero_bytes, success=True)
        self.test_null_data_transaction(node=self.nodes[1], data=zero_bytes, success=False)
        self.test_null_data_transaction(node=self.nodes[2], data=zero_bytes, success=True)
        self.test_null_data_transaction(node=self.nodes[3], data=zero_bytes, success=True)

        self.log.info("Testing a null data transaction with one byte of data.")
        self.test_null_data_transaction(node=self.nodes[0], data=one_byte, success=True)
        self.test_null_data_transaction(node=self.nodes[1], data=one_byte, success=False)
        self.test_null_data_transaction(node=self.nodes[2], data=one_byte, success=True)
        self.test_null_data_transaction(node=self.nodes[3], data=one_byte, success=False)

        # Test -mindatacarriersize
        # OP_RETURN + push opcode + data = total script size
        # For 10 byte minimum: we need 7 bytes of data (1 OP_RETURN + 1 push opcode + 7 data = 9 bytes)
        # Actually for 10 bytes: we need 8 bytes of data (1 OP_RETURN + 1 push opcode + 8 data = 10 bytes)
        nine_byte_script = randbytes(7)  # Will create 9 byte script (below minimum)
        ten_byte_script = randbytes(8)   # Will create 10 byte script (exactly at minimum)
        eleven_byte_script = randbytes(9) # Will create 11 byte script (above minimum)

        self.log.info("Testing minimum datacarrier size with no OP_RETURN (should fail).")
        tx_no_opreturn = self.wallet.create_self_transfer(fee_rate=0)["tx"]
        tx_no_opreturn.vout[0].nValue -= tx_no_opreturn.get_vsize()
        assert_raises_rpc_error(-26, "datacarrier-too-small", self.wallet.sendrawtransaction, from_node=self.nodes[4], tx_hex=tx_no_opreturn.serialize().hex())

        self.log.info("Testing minimum datacarrier size below minimum (9 bytes, minimum is 10).")
        self.test_null_data_transaction(node=self.nodes[4], data=nine_byte_script, success=False)

        self.log.info("Testing minimum datacarrier size exactly at minimum (10 bytes).")
        self.test_null_data_transaction(node=self.nodes[4], data=ten_byte_script, success=True)

        self.log.info("Testing minimum datacarrier size above minimum (11 bytes).")
        self.test_null_data_transaction(node=self.nodes[4], data=eleven_byte_script, success=True)

        # Clean shutdown boilerplate due to deprecation
        self.expected_stderr = [
            "",  # node 0 has no deprecated options
            "Warning: Options '-datacarrier' or '-datacarriersize' are set but are marked as deprecated and are expected to be removed in a future version.",
            "Warning: Options '-datacarrier' or '-datacarriersize' are set but are marked as deprecated and are expected to be removed in a future version.",
            "Warning: Options '-datacarrier' or '-datacarriersize' are set but are marked as deprecated and are expected to be removed in a future version.",
            "Warning: Options '-datacarrier' or '-datacarriersize' are set but are marked as deprecated and are expected to be removed in a future version.",
        ]

        for i in range(self.num_nodes):
            self.stop_node(i, expected_stderr=self.expected_stderr[i])


if __name__ == '__main__':
    DataCarrierTest(__file__).main()
