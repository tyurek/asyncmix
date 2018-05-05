import gevent
class Writer:
    def __init__ (self, recv_function):
        f = open("deletme", "w+")
        while True:
            msg = recv_function()
            if msg == "killme":
                f.close()
                break
            f.write(msg + "\n")
