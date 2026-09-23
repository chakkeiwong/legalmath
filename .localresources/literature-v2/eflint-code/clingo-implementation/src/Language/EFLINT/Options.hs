{-# LANGUAGE LambdaCase #-}

module Language.EFLINT.Options where

import Language.EFLINT.Util

import Control.Monad (when)

import System.Directory
import System.IO.Unsafe
import Data.IORef
import Data.List(isPrefixOf)
import Data.Maybe(isJust)

type Options = IORef OptionsStruct

data OptionsStruct = OptionsStruct {
        include_paths   :: [FilePath]
      , included_files  :: [FilePath]
      , filepath        :: Maybe FilePath
      , input           :: [Bool]
      , ignore_scenario :: Bool
      , debug           :: Bool
      , accept_phrases  :: Bool
      , test_mode       :: Bool
        -- Encodes "Given?" -> "Path specified?"
      , clingo          :: Maybe (Maybe FilePath)
      , clingo_no_libs  :: Bool
      , clingo_pretty   :: Bool
      }

find :: (OptionsStruct -> a) -> Options -> a
find proj = proj . unsafePerformIO . readIORef

defaultOptionsStruct = OptionsStruct {
    include_paths   = []
  , included_files  = []
  , filepath        = Nothing
  , input           = []
  , ignore_scenario = False
  , debug           = False
  , test_mode       = False
  , accept_phrases  = False
  , clingo          = Nothing
  , clingo_no_libs  = False
  , clingo_pretty   = False
  }

is_in_test_mode :: Options -> IO Bool
is_in_test_mode opts = test_mode <$> readIORef opts

run_options :: [String] -> IO Options
run_options args = do
  ref <- newIORef defaultOptionsStruct
  run_options' args ref
  return ref
 where
  run_options' [] opts = return ()
  run_options' ("--ignore-scenario":args) opts = do
    modifyIORef opts (\os -> os { ignore_scenario = True } )
    run_options' args opts
  run_options' ("--debug":args) opts = do
    modifyIORef opts (\os -> os { debug = True })
    run_options' args opts
  run_options' ("--test-mode":args) opts = do -- errors and failed queries only
    modifyIORef opts (\os -> os { test_mode = True })
    run_options' args opts
  run_options' ("--accept-phrases":args) opts = do
    modifyIORef opts (\os -> os { accept_phrases = True })
    run_options' args opts
  run_options' ("-i":(sdir:args)) opts = add_include_path sdir opts >> run_options' args opts
  run_options' ("--clingo":[]) opts = set_clingo opts Nothing >> run_options' args opts
  run_options' ("--clingo":(next:args)) opts | (isPrefixOf "-" next) = set_clingo opts Nothing >> run_options' args opts
  run_options' ("--clingo":(path:args)) opts = set_clingo opts (Just path) >> run_options' args opts
  -- run_options' ("--clingo-pretty":args) opts = set_clingo_pretty opts True >> run_options' args opts
  run_options' ("--clingo-no-libs":args) opts = set_clingo_no_libs opts True >> run_options' args opts
  run_options' (_:args) opts = run_options' args opts

add_include_path :: String -> Options -> IO ()
add_include_path fp opts = doesDirectoryExist fp >>= \case
    False -> return ()
    True  -> modifyIORef opts (\os -> os {include_paths = include_paths os ++ [fp] })

add_include :: String -> Options -> IO ()
add_include fp opts = doesFileExist fp >>= \case
    False -> return ()
    True  -> modifyIORef opts (\os -> os {included_files = included_files os ++ [fp] })

has_been_included :: FilePath -> Options -> Bool
has_been_included file opts = unsafePerformIO $ do
  dirs <- include_paths <$> readIORef opts
  files <- included_files <$> readIORef opts
  files' <- mapM canonicalizePath files
  find_included_file dirs file >>= \case
    []        -> return False
    (file:_)  -> (`elem` files') <$> canonicalizePath file


add_filepath :: FilePath -> Options -> IO ()
add_filepath fp opts = do modifyIORef opts (\os -> os { filepath = Just fp })

add_input :: [String] -> Options -> IO ()
add_input ss opts = modifyIORef opts (\os -> os { input = map readAssignmentMaybe ss })

set_clingo :: Options -> Maybe FilePath -> IO ()
set_clingo opts value = modifyIORef opts (\os -> os { clingo = Just value })
get_clingo :: Options -> Maybe (Maybe FilePath)
get_clingo opts = (unsafePerformIO (clingo <$> readIORef opts))
-- set_clingo_pretty :: Options -> Bool -> IO ()
-- set_clingo_pretty opts value = modifyIORef opts (\os -> os { clingo_pretty = value })
set_clingo_no_libs :: Options -> Bool -> IO ()
set_clingo_no_libs opts value = modifyIORef opts (\os -> os { clingo_no_libs = value })

consume_input :: Options -> IO (Maybe Bool)
consume_input opts = do
  optss <- readIORef opts
  case input optss of
    [] -> return Nothing
    bs -> do modifyIORef opts (\os -> os { input = tail bs })
             return (Just $ head bs)

readAssignmentMaybe :: String -> Bool
readAssignmentMaybe s = case s of
                "True"  -> True
                "true"  -> True
                "t"     -> True
                "T"     -> True
                "y"     -> True
                "Y"     -> True
                "False" -> False
                "false" -> False
                "f"     -> False
                "F"     -> False
                "N"     -> False
                "n"     -> False
                _       -> False

verbosity :: Options -> Level -> IO () -> IO ()
verbosity opts loc_level m = do
  limit <- limitM <$> readIORef opts
  when (not(limit == Silent) && loc_level <= limit) m
  where limitM opts  | debug     opts       = Verbose
                     | test_mode opts       = TestMode
                     | isJust (clingo opts) = Silent
                     | otherwise            = Default

data Level = TestMode | Default | Verbose | Silent deriving (Ord, Enum, Eq)
