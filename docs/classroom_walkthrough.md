# Classroom walkthrough

## Explain the three groups

> Gray had no practice. Blue practiced for twelve episodes but could not save notes. Purple had the same twelve practice episodes and could also keep a memory file. So gray versus blue tests exploration, while blue versus purple tests the added value of memory.

## Explain the animation

> All three final controllers are running on exactly the same new map. The gray controller chooses a reasonable route, but it turns too late and keeps making contact with the obstacle. The two explored controllers turn earlier and leave more space, so both reach the goal without contact. The coding agent is no longer involved here. We are only watching the final Python code it produced.

## Explain the result

> The main difference is reliability. Zero-shot still succeeded in twenty-three of the twenty-four episodes, but it made one hundred contacts. Both explored controllers completed every episode without contact and used fewer steps. So online feedback helped in this run. The effect of the memory file is less clear. It did not improve the result in this replicate, but one generated controller per condition is not enough to conclude that memory is useless.

## Discussion question

> In my experiment, exploration clearly helped, but adding memory did not improve the controller in this run. Is RAX improving mainly because the agent interacts with the environment, or because it can save what it learns? How could we test those effects separately?

