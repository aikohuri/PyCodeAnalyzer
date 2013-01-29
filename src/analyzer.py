import optparse

import wx

from gui import analyzer_frame


def getOptions():
    parser = optparse.OptionParser("usage: %prog [option arg1 [option2 arg2]]")
    parser.add_option("-f", "--file", dest="projFilePath", default="", type="string", metavar="FILE",
                      help="Project setting file")
    parser.add_option("-e", "--execute", dest="execute", action="store_true", default=False,
                      help="Execute analysis")
    parser.add_option("-p", "--pipeline", dest="pipeline", action="store_true", default=False,
                      help="Execute analysis using pipeline")
    parser.add_option("-m", "--multiprocessing", dest="multiprocessing", action="store_true", default=False,
                      help="Execute analysis using multiprocessing")
    parser.add_option("--np", dest="numProc", default="1", type="int",
                      help="Number of processes. This is used when -m/--multiprocessing flag is set.")
    parser.add_option("--npp", dest="numPpProc", default="1", type="int",
                      help='''Number of preprocessor processes. This is used when both -p/--pipeline and
                              -m/--multiprocessing flags are set.''')
    parser.add_option("--nparser", dest="numParserProc", default="1", type="int",
                      help='''Number of parser processes. This is used when both -p/--pipeline and
                              -m/--multiprocessing flags are set.''')
    options, args = parser.parse_args()
    return options

def main():
    opt = getOptions()

    app = wx.App(0)

    frame = analyzer_frame.MainFrame(opt)
    frame.CenterOnParent()
    frame.Show()
    
    app.MainLoop()


if __name__ == '__main__':
    main()

