from time import sleep
from Exemple import Process

def launch(nbProcess, runningTime=5):
    processes = []

    for i in range(nbProcess):
        processes = processes + [Process("P"+str(i))]

    sleep(runningTime)

    for p in processes:
        p.stop()

if __name__ == '__main__':

    #bus = EventBus.getInstance()
    
    launch(nbProcess=3, runningTime=5)

    #bus.stop()