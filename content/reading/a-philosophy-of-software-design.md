---
title: "A Philosophy of Software Design"
date: 2026-03-02
draft: false

params:
  author: "John K. Ousterhout"
  kindle_title: "A Philosophy of Software Design, 2nd Edition"
  date_started: 2026-03-02
  date_finished: 2026-04-20
  fiction: false
---

<!-- kindle-highlights:start -->

> One of the most important techniques for managing software complexity is to design systems so that developers only need to face a small fraction of the overall complexity at any given time. This approach is called modular design, and this chapter presents its basic principles.

> When designing modules, focus on the knowledge that’s needed to perform each task, not the order in which tasks occur.

> Defaults illustrate the principle that interfaces should be designed to make the common case as simple as possible.

> When decomposing a system into modules, try not to be influenced by the order in which operations will occur at runtime; that will lead you down the path of temporal decomposition, which will result in information leakage and shallow modules. Instead, think about the different pieces of knowledge that are needed to carry out the tasks of your application, and design each module to encapsulate one or a few of those pieces of knowledge. This will produce a clean and simple design with deep modules.

> Special cases can result in code that is riddled with if statements, which make the code hard to understand and are prone to bugs. Thus, special cases should be eliminated wherever possible. The best way to do this is by designing the normal case in a way that automatically handles the edge conditions without any extra code.

> Thus, you should avoid configuration parameters as much as possible. Before exporting a configuration parameter, ask yourself: “will users (or higher-level modules) be able to determine a better value than we can determine here?” When you do create configuration parameters, see if you can provide reasonable defaults, so users will only need to provide values under exceptional conditions. Ideally, each module should solve a problem completely; configuration parameters result in an incomplete solution, which adds to system complexity.

> Exception handling is one of the worst sources of complexity in software systems. Code that deals with special conditions is inherently harder to write than code that deals with normal cases, and developers often define exceptions without considering how they will be handled.

> I have noticed that the design-it-twice principle is sometimes hard for really smart people to embrace. When they are growing up, smart people discover that their first quick idea about any problem is sufficient for a good grade; there is no need to consider a second or third possibility. This tends to result in bad work habits. However, as these people get older, they get promoted into environments with harder and harder problems. Eventually, everyone reaches a point where your first ideas are no longer good enough; if you want to get really great results, you have to consider a second possibility, or perhaps a third, no matter how smart you are. The design of large software systems falls in this category: no-one is good enough to get it right with their first try.

> The reason for writing comments is that statements in a programming language can’t capture all of the important information that was in the mind of the developer when the code was written. Comments record this information so that developers who come along later can easily understand and modify the code. The guiding principle for comments is that comments should describe things that aren’t obvious from the code.

> The most important comments are those in the first two categories. Every class should have an interface comment, every class variable should have a comment, and every method should have an interface comment.

> After you have written a comment, ask yourself the following question: could someone who has never seen the code write the comment just by looking at the code next to the comment? If the answer is yes, as in the examples above, then the comment doesn’t make the code any easier to understand. Comments like these are why some people think that comments are worthless.

> A first step towards writing good comments is to use different words in the comment from those in the name of the entity being described.

> Engineers tend to be very detail-oriented. We love details and are good at managing lots of them; this is essential for being a good engineer. But, great software designers can also step back from the details and think about a system at a higher level.

> Selecting names for variables, methods, and other entities is one of the most underrated aspects of software design.

> A good name conveys a lot of information about what the underlying entity is, and, just as important, what it is not. When considering a particular name, ask yourself: “If someone sees this name in isolation, without seeing its declaration, its documentation, or any code that uses the name, how closely will they be able to guess what the name refers to? Is there some other name that will paint a clearer picture?”

> If you find it difficult to come up with a name for a particular variable that is precise, intuitive, and not too long, this is a red flag. It suggests that the variable may not have a clear definition or purpose. When this happens, consider alternative factorings.

> Gerrand makes one comment that I agree with: “The greater the distance between a name’s declaration and its uses, the longer the name should be.”

> Many developers put off writing documentation until the end of the development process, after coding and unit testing are complete. This is one of the surest ways to produce poor quality documentation. The best time to write comments is at the beginning of the process, as you write the code. Writing the comments first makes documentation part of the design process. Not only does this produce better documentation, but it also produces better designs and it makes the process of writing documentation more enjoyable.

> Chapter 3 introduced the distinction between tactical programming and strategic programming: in tactical programming, the primary goal is to get something working quickly, even if that results in additional complexity; in strategic programming, the most important goal is to produce a great system design.

> Whenever you modify any code, try to find a way to improve the system design at least a little bit in the process. If you’re not making the design better, you are probably making it worse.

> Don’t change existing conventions. Resist the urge to “improve” on existing conventions. Having a “better idea” is not a sufficient excuse to introduce inconsistencies. Your new idea may indeed be better, but the value of consistency over inconsistency is almost always greater than the value of one approach over another.

> This example illustrates a general rule: software should be designed for ease of reading, not ease of writing.

> Thus, implementation inheritance should be used with caution. Before using implementation inheritance, consider whether an approach based on composition can provide the same benefits. For instance, it may be possible to use small helper classes to implement the shared functionality. Rather than inheriting functions from a parent, the original classes can each build upon the features of the helper classes.

> Unit tests are the ones most often written by developers. They are small and focused: each test usually validates a small section of code in a single method. Unit tests can be run in isolation, without setting up a production environment for the system. Unit tests are often run in conjunction with a test coverage tool to ensure that every line of code in the application is tested.

> The second kind of test consists of system tests (sometimes called integration tests), which ensure that the different parts of an application all work together properly. They typically involve running the entire application under conditions similar to production. System tests are more likely to be written by a separate QA or testing team.

> Although I am a strong advocate of unit testing, I am not a fan of test-driven development. The problem with test-driven development is that it focuses attention on getting specific features working, rather than finding the best design. This is tactical programming pure and simple, with all of its disadvantages.

> One place where it makes sense to write the tests first is when fixing bugs. Before fixing a bug, write a unit test that fails because of the bug.

> This chapter discusses how to achieve high performance without sacrificing clean design. The most important idea is still simplicity: not only does simplicity improve a system’s design, but it usually makes systems faster.

> It’s tempting to rush off and start making performance tweaks, based on your intuitions about what is slow. Don’t do this! Programmers’ intuitions about performance are unreliable. This is true even for experienced developers. If you start making changes based on intuition, you’ll waste time on things that don’t actually improve performance, and you’ll probably make the system more complicated in the process.

> Ideally, there will be a single if statement at the beginning, which detects all special cases with one test. In the normal case, only this one test will need to be made, after which the critical path can be executed with no additional tests for special cases. If the initial test fails (which means a special case has occurred) the code can branch to a separate place off the critical path to handle it.

> 21.2  Minimize what matters Try to make as little matter as possible: this will result in simpler systems. For example, try to minimize the number of parameters that must be specified to construct an object, or provide default values that reflect most common usage. For things that do matter, try to minimize the number of places where they matter. Information that is hidden within a module doesn’t matter to code outside that module. If an exception can be handled entirely at a low level in a system, then it doesn’t matter to the rest of the system. If a configuration parameter can be computed automatically based on system behavior (rather than exposing it for an administrator to choose manually) then it no longer matters to administrators.

> The phrase “good taste” describes the ability to distinguish what is important from what isn’t important. Having good taste is an important part of being a good software designer.

> On the other hand, if good design is an important goal for you, then the ideas in this book should make programming more fun. Design is a fascinating puzzle: how can a particular problem be solved with the simplest possible structure? It’s fun to explore different approaches, and it’s a great feeling to discover a solution that is both simple and powerful. A clean, simple, and obvious design is a beautiful thing.

> Here are the most important software design principles discussed in this book: Complexity is incremental: you have to sweat the small stuff (see p. 11). Working code isn’t enough (see p. 14). Make continual small investments to improve system design (see p. 15). Modules should be deep (see p. 23) Interfaces should be designed to make the most common usage as simple as possible (see p. 27). It’s more important for a module to have a simple interface than a simple implementation (see pp. 61, 74).

<!-- kindle-highlights:end -->
