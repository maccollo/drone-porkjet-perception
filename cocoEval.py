cocoEval = COCOeval(cocoGt,cocoDt,annType)
cocoEval.params.maxDets = [200]
cocoEval.params.imgIds  = imgIdsDt
cocoEval.evaluate()
cocoEval.accumulate()
cocoEval.summarize_2() # instead of calling cocoEval.summarize()


def summarize_2(self):
    # Copy everything from `summarize` method here except
    # the function `_summarizeDets()`.
    def _summarizeDets():
        stats = np.zeros((12,))
        stats[0] = _summarize(1, maxDets=self.params.maxDets[0])
        stats[1] = _summarize(1, iouThr=.5, maxDets=self.params.maxDets[0])
        stats[2] = _summarize(1, iouThr=.75, maxDets=self.params.maxDets[0])
        stats[3] = _summarize(1, areaRng='small', maxDets=self.params.maxDets[0])
        stats[4] = _summarize(1, areaRng='medium', maxDets=self.params.maxDets[0])
        stats[5] = _summarize(1, areaRng='large', maxDets=self.params.maxDets[0])
        stats[6] = _summarize(0, maxDets=self.params.maxDets[0])
        stats[9] = _summarize(0, areaRng='small', maxDets=self.params.maxDets[0])
        stats[10] = _summarize(0, areaRng='medium', maxDets=self.params.maxDets[0])
        stats[11] = _summarize(0, areaRng='large', maxDets=self.params.maxDets[0])
        return stats
    # Copy other things which are left from `summarize()` here.