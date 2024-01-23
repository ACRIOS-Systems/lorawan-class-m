import matplotlib.pyplot as plt

# PLT CONFIGURATION
plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'lmodern'

# DEBUGGING FUNCTIONS
def plotSignalX(s, tit, xlab, ylab, xaxis = None):
    plt.plot(xaxis, s)
    plt.title(r'\textbf{%s}' %(tit))
    plt.xlabel(r'\textbf{%s}' %(xlab))
    plt.ylabel(r'\textbf{%s}' %(ylab))
    #plt.show()

    # plt.xlabel(r'\textbf{Vzorky [\textit{-}]}')
    # plt.ylabel(r'\textbf{df/dt [\textit{Hz}]}')

def plotSignal(s, tit, xlab, ylab):
    plt.plot(s)
    plt.title(r'\textbf{%s}' %(tit))
    plt.xlabel(r'\textbf{%s}' %(xlab))
    plt.ylabel(r'\textbf{%s}' %(ylab))
   # plt.show()


def plotSubplotX(s1, tit1, xlab1, ylab1, t1, s2, tit2, xlab2, ylab2, t2):
    plt.subplot(2, 1, 1)
    plt.plot(t1, s1)
    plt.title(r'\textbf{%s}' %(tit1))
    plt.xlabel(r'\textbf{%s}' %(xlab1))
    plt.ylabel(r'\textbf{%s}' %(ylab1))
    plt.subplot(2, 1, 2)
    plt.plot(t2, s2)
    plt.title(r'\textbf{%s}' %(tit2))
    plt.xlabel(r'\textbf{%s}' %(xlab2))
    plt.ylabel(r'\textbf{%s}' %(ylab2))
    #plt.show()