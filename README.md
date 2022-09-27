# Nowcasting API

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-9-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

[![codecov](https://codecov.io/gh/openclimatefix/nowcasting_api/branch/main/graph/badge.svg?token=W7L3X72M1O)](https://codecov.io/gh/openclimatefix/nowcasting_api)


API for hosting nowcasting solar predictions.
Will just return 'dummy' numbers until about mid-2022!

We use [FastAPI](https://fastapi.tiangolo.com/).

# Documentation

Documentation can be viewed at `/docs`. This is automatically generated from the code.

# Setup and Run

This can be done it two different ways: With Python or with Docker.

## Python

### Create a virtual env

```bash
python3 -m venv ./venv
source venv/bin/activate
```

### Install Requirements and Run

```bash
pip install -r requirements.txt
cd src && uvicorn main:app --reload
```

## Docker

1. Make sure docker is installed on your system.
2. Use `docker-compose up`
   in the main directory to start up the application.
3. You will now be able to access it on `http://localhost:80`

### Tests

TO run tests use the following command
```bash
docker-compose -f test-docker-compose.yml build
docker-compose -f test-docker-compose.yml run api
```

# Development

We use `pre-commit` to manage various pre-commit hooks. All hooks are also run
as Actions when code is pushed to GitHub.

You can run the formatters and linters locally. To do that:

1. [Install pre-commit](https://pre-commit.com/#install)
2. Check the install worked via `pre-commit --version`
3. Install the git hooks script via `pre-commit install`

# Deployment

This API is temporarily deployed on AWS Elastic Beanstalk.
We will move it to a more stable service once the API matures.

If you want to deploy a new release, then please adjust the version in `docker-compose.yml`.

```bash
eb init
eb deploy --message="Add message here"
```

# Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center"><a href="https://github.com/peterdudfield"><img src="https://avatars.githubusercontent.com/u/34686298?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Peter Dudfield</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=peterdudfield" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/mdfaisal98"><img src="https://avatars.githubusercontent.com/u/64960915?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Mohammed Faisal</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=mdfaisal98" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/BodaleDenis"><img src="https://avatars.githubusercontent.com/u/60345186?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Bodale Denis</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=BodaleDenis" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/OBITORASU"><img src="https://avatars.githubusercontent.com/u/65222459?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Souhit Dey</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=OBITORASU" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/flowirtz"><img src="https://avatars.githubusercontent.com/u/6052785?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Flo</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=flowirtz" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/vnshanmukh"><img src="https://avatars.githubusercontent.com/u/67438038?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Shanmukh</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=vnshanmukh" title="Code">💻</a></td>
      <td align="center"><a href="http://www.sixte.demaupeou.com"><img src="https://avatars.githubusercontent.com/u/17206983?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Sixte de Maupeou</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=sixtedemaupeou" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center"><a href="https://github.com/rachel-labri-tipton"><img src="https://avatars.githubusercontent.com/u/86949265?v=4?s=100" width="100px;" alt=""/><br /><sub><b>rachel tipton</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=rachel-labri-tipton" title="Code">💻</a></td>
      <td align="center"><a href="https://github.com/braddf"><img src="https://avatars.githubusercontent.com/u/41056982?v=4?s=100" width="100px;" alt=""/><br /><sub><b>braddf</b></sub></a><br /><a href="https://github.com/openclimatefix/nowcasting_api/commits?author=braddf" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
