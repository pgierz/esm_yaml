#!/usr/bin/env python
import sys, getopt, esm_calendar


def main(args):
    if args.index("--") == len(args) - 4:
        unit = args[-1]
        args = args[:-1]
    else:
        unit = "seconds"

    sdate1 = args[-2]
    sdate2 = args[-1]
    args = args[:-3]
    try:
        optlist, rest = getopt.getopt(args, "c:")
    except getopt.GetoptError as err:
        print(str(err))  # will print something like "option -a not recognized"
        # usage()
        sys.exit(2)
    calendar_type = 1
    for o, a in optlist:
        if o == "-c":
            calendar_type = int(a)
        else:
            assert False, "unhandled option"
    cal = esm_calendar.Calendar(calendar_type)
    date1 = esm_calendar.Date(sdate1, cal)
    date2 = esm_calendar.Date(sdate2, cal)
    print(date1.time_between(date2, unit))


main(sys.argv[1:])
