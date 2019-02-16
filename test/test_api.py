import pytest
import trio

import pynng

from test._test_util import wait_pipe_len


addr = 'tcp://127.0.0.1:13131'
addr2 = 'tcp://127.0.0.1:13132'


def test_dialers_get_added():
    with pynng.Pair0() as s:
        assert len(s.dialers) == 0
        s.dial(addr, block=False)
        assert len(s.dialers) == 1
        s.dial(addr2, block=False)
        assert len(s.dialers) == 2


def test_listeners_get_added():
    with pynng.Pair0() as s:
        assert len(s.listeners) == 0
        s.listen(addr)
        assert len(s.listeners) == 1
        s.listen(addr2)
        assert len(s.listeners) == 2


def test_closing_listener_works():
    with pynng.Pair0(listen=addr) as s:
        assert len(s.listeners) == 1
        s.listeners[0].close()
        assert len(s.listeners) == 0
        # if the listener is really closed, we should be able to listen at the
        # same address again
        s.listen(addr)
        assert len(s.listeners) == 1
    assert len(s.listeners) == 0


def test_closing_dialer_works():
    with pynng.Pair0(dial=addr, block_on_dial=False) as s:
        assert len(s.dialers) == 1
        s.dialers[0].close()
    assert len(s.listeners) == 0


def test_nonblocking_recv_works():
    with pynng.Pair0(listen=addr) as s:
        with pytest.raises(pynng.TryAgain):
            s.recv(block=False)


def test_context():
    async def test_them_up(req, rep):
        assert isinstance(req, pynng.Context)
        assert isinstance(rep, pynng.Context)
        request = b'i am requesting'
        await req.asend(request)
        assert await rep.arecv() == request

        response = b'i am responding'
        await rep.asend(response)
        assert await req.arecv() == response

        with pytest.raises(pynng.BadState):
            await req.arecv()

        # responders can't send before receiving
        with pytest.raises(pynng.BadState):
            await rep.asend(b'I cannot do this why am I trying')

    with pynng.Req0(listen=addr, recv_timeout=1000) as req, \
            pynng.Rep0(dial=addr, recv_timeout=1000) as rep:
        with req.new_context() as req_ctx, rep.new_context() as rep_ctx:
            trio.run(test_them_up, req_ctx, rep_ctx)


def test_multiple_contexts():
    async def recv_and_send(ctx):
        data = await ctx.arecv()
        await trio.sleep(0.05)
        await ctx.asend(data)

    async def do_some_stuff(rep, req1, req2):
        async with trio.open_nursery() as n:
            ctx1, ctx2 = [rep.new_context() for _ in range(2)]
            n.start_soon(recv_and_send, ctx1)
            n.start_soon(recv_and_send, ctx2)

            await req1.asend(b'oh hi')
            await req2.asend(b'me toooo')
            assert (await req1.arecv() == b'oh hi')
            assert (await req2.arecv() == b'me toooo')

    with pynng.Rep0(listen=addr, recv_timeout=500) as rep, \
            pynng.Req0(dial=addr, recv_timeout=500) as req1, \
            pynng.Req0(dial=addr, recv_timeout=500) as req2:
        trio.run(do_some_stuff, rep, req1, req2)


def test_synchronous_recv_context():
    with pynng.Rep0(listen=addr, recv_timeout=500) as rep, \
            pynng.Req0(dial=addr, recv_timeout=500) as req:
        req.send(b'oh hello there old pal')
        assert rep.recv() == b'oh hello there old pal'
        rep.send(b'it is so good to hear from you')
        assert req.recv() == b'it is so good to hear from you'


def test_pair1_polyamorousness():
    with pynng.Pair1(listen=addr, polyamorous=True, recv_timeout=500) as s0, \
            pynng.Pair1(dial=addr, polyamorous=True, recv_timeout=500) as s1:
            wait_pipe_len(s0, 1)
            # pipe for s1 .
            p1 = s0.pipes[0]
            with pynng.Pair1(dial=addr, polyamorous=True, recv_timeout=500) as s2:
                wait_pipe_len(s0, 2)
                # pipes is backed by a dict, so we can't rely on order in
                # Python 3.5.
                pipes = s0.pipes
                p2 = pipes[1]
                if p2 is p1:
                    p2 = pipes[0]
                p1.send(b'hello s1')
                assert s1.recv() == b'hello s1'

                p2.send(b'hello there s2')
                assert s2.recv() == b'hello there s2'


def test_sub_sock_options():
    with pynng.Pub0(listen=addr) as pub:
        # test single option topic
        with pynng.Sub0(dial=addr, topics='beep') as sub:
            wait_pipe_len(sub, 1)
            pub.send(b'beep hi')
            assert sub.recv() == b'beep hi'
        with pynng.Sub0(dial=addr, topics=['beep', 'hello']) as sub:
            wait_pipe_len(sub, 1)
            pub.send(b'beep hi')
            pub.send(b'hello there')
            assert sub.recv() == b'beep hi'
            assert sub.recv() == b'hello there'

