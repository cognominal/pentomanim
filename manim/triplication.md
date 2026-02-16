# Deep First Search

This video demonstrate the use of
[DFS](https://en.wikipedia.org/wiki/Depth-first_search) algorithm.
Such algorithm walk a tree of state. Here the state is the state of the board
so we represent the board at each node.

to search the tree of possibilty of a fitting problem.

and how pruning improves its performance.

Eliminating the hopeless branches save time. So the mod-5 variant verify that all connected
free squares of the board are sets of a cardinality multiple of 5. In other word
we can fit pentominos there.

The manim generated graph demonstrate the solving of the
[triplication](https://www.cimt.org.uk/resources/puzzles/pentoes/penttrip.htm) of a pentominoe.
A given node represent a state of the search, its children represent the next step
The fitting of all the  orientation of all the free pentamino on the next free square.
The orientations that fits are a subset of the possible orientation.
Also we represent only the first fitting orientation of each note

We represent only part of the tree, up to depth three and only at most hree children per node.
