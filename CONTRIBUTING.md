# gnewcash Contributions

## Pull Requests

1. If your changes include any documentable changes (i.e. not bugfixes), please make sure you update the Sphinx 
documentation with your new method. Your pull request may be rejected if docs aren't included.
2. If your changes should be included in the README, please update it.
3. All your changes should be covered by good unit tests. Your pull request may be rejected if code isn't covered by
test, or if unit tests start to fail.
4. All your changes should pass both flake8 and pylint linters with the "dev" packages installed. Your pull request may
be rejected if your changes introduce lint errors.

## Git Flow

GNewCash uses the [Gitflow workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow) for 
release cycles. Your pull request should go into a feature branch of gnewcash for validation.

## Getting Set Up

Fork the repository to your GitHub account and clone it. You'll need [poetry](https://poetry.eustace.io/)
to install the dependencies of the project. To do so, run ```poetry install```.

After dependencies are installed, run ```poetry shell``` and run the following commands:

1. ```flake8 gnewcash```
2. ```pylint gnewcash```
3. ```coverage run -m unittest discover```

All 3 should succeed without issues.