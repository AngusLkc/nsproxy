"""
iperf3 Tests
============================

These tests verify nsproxy's TCP performance and scalability with iperf3,
in both upload and download directions.

Stress Tests:
------------------------------------------
test_iperf3_stress_direct_upload
    Tests upload in direct mode (-D flag) without proxy.

test_iperf3_stress_direct_download
    Tests download in direct mode (-D flag) without proxy.

test_iperf3_stress_http_upload
    Tests upload through HTTP proxy.

test_iperf3_stress_http_download
    Tests download through HTTP proxy.

test_iperf3_stress_socks5_upload
    Tests upload through SOCKS5 proxy.

test_iperf3_stress_socks5_download
    Tests download through SOCKS5 proxy.

Fairness Tests:
------------------------------------------
test_iperf3_fairness_direct_upload
    Tests upload fairness in direct mode (-D flag) without proxy.

test_iperf3_fairness_direct_download
    Tests download fairness in direct mode (-D flag) without proxy.

test_iperf3_fairness_http_upload
    Tests upload fairness through HTTP proxy.

test_iperf3_fairness_http_download
    Tests download fairness through HTTP proxy.

test_iperf3_fairness_socks5_upload
    Tests upload fairness through SOCKS5 proxy.

test_iperf3_fairness_socks5_download
    Tests download fairness through SOCKS5 proxy.

Usage:
------
    pytest -v tests/test_iperf3.py
    pytest -v -k "iperf3" tests/
"""

import json
import statistics
import subprocess
import time
from .conftest import (
    LOCAL_IP,
    HTTP_NOAUTH_PORT,
    SOCKS_NOAUTH_PORT,
    wait_server,
    managed_proc,
)

IPERF3_PORT = 37778
IPERF3_DURATION = 3
IPERF3_STRESS_CONNECTIONS = 128
IPERF3_FAIRNESS_CONNECTIONS = 8
TEST_TIMEOUT = 5


def _run_iperf3_stress_test(nsproxy_runner, extra_args, reverse=False):
    """Run iperf3 stress test through nsproxy"""
    server_args = [
        "iperf3",
        "-i", "0",
        "--forceflush",
        "-s",
        "-p", str(IPERF3_PORT)
    ]
    client_args = [
        "iperf3",
        "-i", "0",
        "--forceflush",
        "-c", LOCAL_IP,
        "-p", str(IPERF3_PORT),
        "-P", str(IPERF3_STRESS_CONNECTIONS),
        "-t", str(IPERF3_DURATION),
    ]
    if reverse:
        client_args.append("-R")

    with managed_proc(subprocess.Popen(
        server_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )) as server:
        wait_server(server, "Server listening on")

        with managed_proc(nsproxy_runner(extra_args + client_args)) as client:
            cl_stdout, cl_stderr = client.communicate(timeout=TEST_TIMEOUT)

        if server.poll() is None:
            server.kill()

        sv_stdout, sv_stderr = server.communicate(timeout=TEST_TIMEOUT)

        cl_out, cl_err, sv_out, sv_err = [
            s.decode(errors="replace") for s in [cl_stdout, cl_stderr, sv_stdout, sv_stderr]
        ]

        assert client.returncode == 0, (
            f"iperf3 client exited with error code {client.returncode}. "
            f"stderr: {cl_err}"
        )
        assert "Done" in cl_out, (
            f"iperf3 client did not complete successfully. "
            f"stdout: {cl_out}, stderr: {cl_err}"
        )


# Direct mode tests

def test_iperf3_stress_direct_upload(nsproxy_runner):
    """Test TCP upload through nsproxy direct mode"""
    _run_iperf3_stress_test(nsproxy_runner, ["-q", "-D"], reverse=False)


def test_iperf3_stress_direct_download(nsproxy_runner):
    """Test TCP download through nsproxy direct mode"""
    _run_iperf3_stress_test(nsproxy_runner, ["-q", "-D"], reverse=True)


# HTTP proxy tests

def test_iperf3_stress_http_upload(proxy_server, nsproxy_runner):
    """Test TCP upload through HTTP proxy"""
    _run_iperf3_stress_test(
        nsproxy_runner,
        ["-q", "-H", "-s", "127.0.0.1", "-p", str(HTTP_NOAUTH_PORT)],
        reverse=False,
    )


def test_iperf3_stress_http_download(proxy_server, nsproxy_runner):
    """Test TCP download through HTTP proxy"""
    _run_iperf3_stress_test(
        nsproxy_runner,
        ["-q", "-H", "-s", "127.0.0.1", "-p", str(HTTP_NOAUTH_PORT)],
        reverse=True,
    )


# SOCKS5 proxy tests

def test_iperf3_stress_socks5_upload(proxy_server, nsproxy_runner):
    """Test TCP upload through SOCKS5 proxy"""
    _run_iperf3_stress_test(
        nsproxy_runner,
        ["-q", "-s", "127.0.0.1", "-p", str(SOCKS_NOAUTH_PORT)],
        reverse=False,
    )


def test_iperf3_stress_socks5_download(proxy_server, nsproxy_runner):
    """Test TCP download through SOCKS5 proxy"""
    _run_iperf3_stress_test(
        nsproxy_runner,
        ["-q", "-s", "127.0.0.1", "-p", str(SOCKS_NOAUTH_PORT)],
        reverse=True,
    )


# Fairness test

def _run_iperf3_fairness_test(nsproxy_runner, extra_args, reverse=False):
    """Run iperf3 fairness test with {IPERF3_FAIRNESS_CONNECTIONS} parallel connections.

    After the test, every connection's transferred bytes must be within 20%
    of the median across all connections.
    """

    server_args = [
        "iperf3",
        "-i", "0",
        "--forceflush",
        "-s",
        "-p", str(IPERF3_PORT)
    ]
    client_args = [
        "iperf3",
        "-i", "0",
        "--forceflush",
        "--json",
        "-c", LOCAL_IP,
        "-p", str(IPERF3_PORT),
        "-P", str(IPERF3_FAIRNESS_CONNECTIONS),
        "-t", str(IPERF3_DURATION),
    ]
    if reverse:
        client_args.append("-R")

    with managed_proc(subprocess.Popen(
        server_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )) as server:
        wait_server(server, "Server listening on")

        with managed_proc(nsproxy_runner(extra_args + client_args)) as client:
            cl_stdout, cl_stderr = client.communicate(timeout=TEST_TIMEOUT)

        if server.poll() is None:
            server.kill()

        sv_stdout, sv_stderr = server.communicate(timeout=TEST_TIMEOUT)

        cl_out, cl_err, sv_out, sv_err = [
            s.decode(errors="replace") for s in [cl_stdout, cl_stderr, sv_stdout, sv_stderr]
        ]

        assert client.returncode == 0, (
            f"iperf3 client exited with error code {client.returncode}. "
            f"stderr: {cl_err}"
        )

        data = json.loads(cl_out)
        if "error" in data and data["error"] is not None:
            assert False, f"iperf3 reported error: {data['error']}"

        streams = data["end"]["streams"]
        assert len(streams) == IPERF3_FAIRNESS_CONNECTIONS, f"Expected {IPERF3_FAIRNESS_CONNECTIONS} streams, got {len(streams)}"

        bytes_list = []
        for stream in streams:
            if reverse:
                bytes_list.append(stream["receiver"]["bytes"])
            else:
                bytes_list.append(stream["sender"]["bytes"])

        median = statistics.median(bytes_list)
        for idx, b in enumerate(bytes_list):
            diff = abs(b - median) / median if median != 0 else float('inf')
            assert diff <= 0.20, (
                f"Stream {idx} unfair: {b} bytes, median={median}, diff={diff:.1%}"
            )


def test_iperf3_fairness_direct_upload(nsproxy_runner):
    """Test TCP upload fairness in direct mode with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(nsproxy_runner, ["-q", "-D"], reverse=False)


def test_iperf3_fairness_direct_download(nsproxy_runner):
    """Test TCP download fairness in direct mode with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(nsproxy_runner, ["-q", "-D"], reverse=True)


def test_iperf3_fairness_http_upload(proxy_server, nsproxy_runner):
    """Test TCP upload fairness through HTTP proxy with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(
        nsproxy_runner,
        ["-q", "-H", "-s", "127.0.0.1", "-p", str(HTTP_NOAUTH_PORT)],
        reverse=False,
    )


def test_iperf3_fairness_http_download(proxy_server, nsproxy_runner):
    """Test TCP download fairness through HTTP proxy with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(
        nsproxy_runner,
        ["-q", "-H", "-s", "127.0.0.1", "-p", str(HTTP_NOAUTH_PORT)],
        reverse=True,
    )


def test_iperf3_fairness_socks5_upload(proxy_server, nsproxy_runner):
    """Test TCP upload fairness through SOCKS5 proxy with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(
        nsproxy_runner,
        ["-q", "-s", "127.0.0.1", "-p", str(SOCKS_NOAUTH_PORT)],
        reverse=False,
    )


def test_iperf3_fairness_socks5_download(proxy_server, nsproxy_runner):
    """Test TCP download fairness through SOCKS5 proxy with {IPERF3_FAIRNESS_CONNECTIONS} concurrent connections"""
    _run_iperf3_fairness_test(
        nsproxy_runner,
        ["-q", "-s", "127.0.0.1", "-p", str(SOCKS_NOAUTH_PORT)],
        reverse=True,
    )
